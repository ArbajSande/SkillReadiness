import React, { useState, useEffect } from 'react';
import { BookOpen, CheckSquare, Square, ExternalLink, Clock, Sparkles, Loader2, AlertCircle, CheckCircle2 } from 'lucide-react';
import { api } from '../api/client';

export default function LearningPathSection({
  targetRole,
  learningPath,
  setLearningPath
}) {
  const [loading, setLoading] = useState(false);
  const [updatingId, setUpdatingId] = useState(null);
  const [error, setError] = useState(null);

  async function handleGeneratePath() {
    setError(null);
    setLoading(true);

    try {
      const res = await api.generateLearningPath(targetRole);
      setLearningPath(res);
    } catch (err) {
      setError(err.message || 'Failed to generate learning roadmap.');
    } finally {
      setLoading(false);
    }
  }

  async function handleToggleItem(itemId, currentStatus) {
    if (updatingId) return;
    setUpdatingId(itemId);
    setError(null);

    try {
      const updated = await api.updateProgress(itemId, !currentStatus);
      setLearningPath(updated);
    } catch (err) {
      setError(err.message || 'Failed to update progress.');
    } finally {
      setUpdatingId(null);
    }
  }

  return (
    <section className="bg-gray-900/60 border border-gray-800 rounded-2xl p-6 sm:p-8 backdrop-blur mt-8 mb-16">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-6">
        <div>
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-semibold bg-purple-500/10 text-purple-400 border border-purple-500/20 mb-2">
            Step 4: Accelerated Learning Plan
          </div>
          <h2 className="text-xl font-bold text-white tracking-tight">Personalized 4-Week Skill Roadmap</h2>
          <p className="text-sm text-gray-400">Targeted modules designed to close specific skill gaps for {targetRole}.</p>
        </div>

        {!learningPath && (
          <button
            onClick={handleGeneratePath}
            disabled={loading}
            className="inline-flex items-center gap-2 px-6 py-2.5 rounded-lg bg-purple-600 hover:bg-purple-500 disabled:opacity-50 text-white text-sm font-semibold transition shadow-lg shadow-purple-600/20"
          >
            {loading ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                <span>Curating Curriculum...</span>
              </>
            ) : (
              <>
                <Sparkles className="w-4 h-4" />
                <span>Generate Curriculum</span>
              </>
            )}
          </button>
        )}
      </div>

      {error && (
        <div className="mb-6 p-4 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-400 text-sm flex items-center gap-3">
          <AlertCircle className="w-5 h-5 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {learningPath && (
        <div className="space-y-6 animate-fade-in">
          {/* Progress Tracker Card */}
          <div className="p-6 rounded-2xl bg-gray-950/80 border border-gray-800 flex flex-col md:flex-row items-center justify-between gap-6">
            <div className="w-full md:w-2/3">
              <div className="flex items-center justify-between text-xs mb-2">
                <span className="font-semibold text-gray-300">Overall Course Progress</span>
                <span className="font-bold text-purple-400">
                  {learningPath.completed_items} of {learningPath.total_items} Modules Completed ({learningPath.overall_progress_percentage}%)
                </span>
              </div>
              <div className="w-full h-3 bg-gray-800 rounded-full overflow-hidden">
                <div
                  className="h-full bg-gradient-to-r from-purple-500 to-indigo-500 rounded-full transition-all duration-500"
                  style={{ width: `${learningPath.overall_progress_percentage}%` }}
                />
              </div>
            </div>

            <div className="flex items-center gap-2 shrink-0">
              {learningPath.overall_progress_percentage === 100 ? (
                <div className="px-4 py-2 rounded-lg bg-emerald-500/15 border border-emerald-500/30 text-emerald-400 text-xs font-bold flex items-center gap-2">
                  <CheckCircle2 className="w-4 h-4" />
                  <span>Curriculum Completed!</span>
                </div>
              ) : (
                <div className="text-xs text-gray-400">
                  Progress auto-saved to database
                </div>
              )}
            </div>
          </div>

          {/* Milestones List */}
          <div className="space-y-5">
            {(learningPath.milestones || []).map((milestone) => (
              <div
                key={milestone.week}
                className="p-6 rounded-2xl bg-gray-950/60 border border-gray-800"
              >
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-4 pb-3 border-b border-gray-800/80">
                  <div className="flex items-center gap-3">
                    <span className="w-7 h-7 rounded-lg bg-purple-500/20 text-purple-400 font-bold text-xs flex items-center justify-center border border-purple-500/30">
                      W{milestone.week}
                    </span>
                    <h3 className="font-semibold text-white text-base">{milestone.title}</h3>
                  </div>
                  <div className="flex flex-wrap gap-1.5">
                    {(milestone.focus_skills || []).map((skill, sIdx) => (
                      <span key={sIdx} className="text-[11px] px-2 py-0.5 rounded bg-gray-800 text-gray-300">
                        {skill}
                      </span>
                    ))}
                  </div>
                </div>

                {/* Items */}
                <div className="space-y-3">
                  {(milestone.items || []).map((item) => {
                    const isUpdating = updatingId === item.id;
                    return (
                      <div
                        key={item.id}
                        onClick={() => handleToggleItem(item.id, item.completed)}
                        className={`p-4 rounded-xl border transition cursor-pointer flex items-start gap-4 ${
                          item.completed
                            ? 'bg-emerald-950/15 border-emerald-800/40 opacity-80'
                            : 'bg-gray-900/40 border-gray-800/80 hover:border-gray-700 hover:bg-gray-900'
                        }`}
                      >
                        <button
                          type="button"
                          className="mt-0.5 text-gray-400 hover:text-white transition shrink-0"
                        >
                          {isUpdating ? (
                            <Loader2 className="w-5 h-5 animate-spin text-purple-400" />
                          ) : item.completed ? (
                            <CheckSquare className="w-5 h-5 text-emerald-400" />
                          ) : (
                            <Square className="w-5 h-5 text-gray-500 hover:text-gray-300" />
                          )}
                        </button>

                        <div className="flex-1">
                          <div className="flex items-center justify-between gap-2">
                            <h4 className={`text-sm font-semibold ${
                              item.completed ? 'line-through text-gray-400' : 'text-white'
                            }`}>
                              {item.title}
                            </h4>
                            <span className="text-[11px] text-gray-400 flex items-center gap-1 shrink-0">
                              <Clock className="w-3.5 h-3.5 text-gray-500" />
                              {item.duration_hours}h
                            </span>
                          </div>
                          <p className="text-xs text-gray-400 mt-1 leading-relaxed">
                            {item.description}
                          </p>
                          {item.resource_url && (
                            <span className="inline-flex items-center gap-1 text-[11px] text-purple-400 mt-2 hover:underline">
                              <span>Curated Learning Material</span>
                              <ExternalLink className="w-3 h-3" />
                            </span>
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </section>
  );
}
