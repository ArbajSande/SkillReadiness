import React, { useState, useEffect } from 'react';
import {
  Target,
  CheckCircle2,
  AlertTriangle,
  ArrowRight,
  Loader2,
  Sparkles,
  AlertCircle,
  TrendingUp,
  Compass,
  History,
  Layers,
  Calendar,
  ShieldCheck
} from 'lucide-react';
import { api } from '../api/client';

export default function ReadinessDashboard({
  targetRole,
  resumeId,
  assessmentId,
  readinessData,
  setReadinessData,
  onProceedToLearningPath
}) {
  const [calculating, setCalculating] = useState(false);
  const [error, setError] = useState(null);
  const [historySnapshots, setHistorySnapshots] = useState([]);
  const [loadingHistory, setLoadingHistory] = useState(false);

  // Fetch authentic readiness history on load or whenever readinessData updates
  useEffect(() => {
    async function fetchHistory() {
      setLoadingHistory(true);
      try {
        const res = await api.getReadinessHistory();
        if (res && res.snapshots) {
          setHistorySnapshots(res.snapshots);
        }
      } catch (err) {
        // Silently tolerate if unauthenticated
      } finally {
        setLoadingHistory(false);
      }
    }
    fetchHistory();
  }, [readinessData]);

  async function handleCalculateReadiness() {
    setError(null);
    setCalculating(true);

    try {
      const res = await api.calculateReadiness(targetRole, resumeId, assessmentId);
      setReadinessData(res);
    } catch (err) {
      setError(err.message || 'Failed to calculate readiness score.');
    } finally {
      setCalculating(false);
    }
  }

  // Level badge styling
  function getLevelBadge(level) {
    switch (level) {
      case 'Job Ready':
        return 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30';
      case 'Near Ready':
        return 'bg-teal-500/15 text-teal-400 border-teal-500/30';
      case 'Intermediate':
        return 'bg-amber-500/15 text-amber-400 border-amber-500/30';
      default:
        return 'bg-rose-500/15 text-rose-400 border-rose-500/30';
    }
  }

  // Format date helper
  function formatDate(isoString) {
    if (!isoString) return 'Just now';
    try {
      const date = new Date(isoString);
      return date.toLocaleDateString(undefined, {
        month: 'short',
        day: 'numeric',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
      });
    } catch {
      return isoString;
    }
  }

  const coreGaps = readinessData?.critical_core_gaps || [];
  const optionalGaps = readinessData?.optional_gaps || [];

  return (
    <section className="bg-gray-900/60 border border-gray-800 rounded-2xl p-6 sm:p-8 backdrop-blur mt-8">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-6">
        <div>
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 mb-2">
            Step 3: Role Readiness Analytics (SR-v2.0-baseline)
          </div>
          <h2 className="text-xl font-bold text-white tracking-tight">AI Readiness Index & Competency Gap</h2>
          <p className="text-sm text-gray-400">
            Weighted Core vs Optional domain matching benchmarked against industry standards for {targetRole}.
          </p>
        </div>

        <button
          onClick={handleCalculateReadiness}
          disabled={calculating}
          className="inline-flex items-center gap-2 px-6 py-2.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white text-sm font-semibold transition shadow-lg shadow-emerald-600/20 shrink-0"
        >
          {calculating ? (
            <>
              <Loader2 className="w-4 h-4 animate-spin" />
              <span>Computing Readiness...</span>
            </>
          ) : (
            <>
              <TrendingUp className="w-4 h-4" />
              <span>{readinessData ? 'Recalculate Readiness' : 'Calculate Readiness'}</span>
            </>
          )}
        </button>
      </div>

      {error && (
        <div className="mb-6 p-4 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-400 text-sm flex items-center gap-3">
          <AlertCircle className="w-5 h-5 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {readinessData && (
        <div className="space-y-8 animate-fade-in">
          {/* Top Score Banner */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {/* Primary Gauge */}
            <div className="p-6 rounded-2xl bg-gradient-to-br from-gray-950 to-gray-900 border border-gray-800 flex flex-col items-center justify-center text-center">
              <span className="text-xs uppercase tracking-wider font-semibold text-gray-400 mb-2">
                Overall Role Readiness
              </span>
              <div className="relative w-32 h-32 flex items-center justify-center my-2">
                <svg className="w-full h-full transform -rotate-90">
                  <circle
                    cx="64"
                    cy="64"
                    r="52"
                    className="stroke-gray-800"
                    strokeWidth="10"
                    fill="transparent"
                  />
                  <circle
                    cx="64"
                    cy="64"
                    r="52"
                    className="stroke-emerald-500 transition-all duration-1000 ease-out"
                    strokeWidth="10"
                    strokeDasharray={326.7}
                    strokeDashoffset={326.7 - (326.7 * (readinessData.overall_readiness_score || 0)) / 100}
                    strokeLinecap="round"
                    fill="transparent"
                  />
                </svg>
                <div className="absolute text-center">
                  <span className="text-3xl font-black text-white tracking-tight">
                    {readinessData.overall_readiness_score}%
                  </span>
                </div>
              </div>
              <span className={`inline-block px-3 py-1 rounded-full text-xs font-bold border mt-2 ${getLevelBadge(readinessData.readiness_level)}`}>
                {readinessData.readiness_level}
              </span>
              <div className="mt-3 text-[11px] text-gray-400 flex items-center gap-1.5">
                <ShieldCheck className="w-3.5 h-3.5 text-blue-400" />
                <span>Coverage: {readinessData.assessment_coverage_pct}% Assessed</span>
              </div>
            </div>

            {/* Category Breakdown Bars */}
            <div className="md:col-span-2 p-6 rounded-2xl bg-gray-950/70 border border-gray-800">
              <h3 className="text-sm font-semibold text-white mb-4">Competency Domain Analysis</h3>
              <div className="space-y-4">
                {(readinessData.category_breakdown || []).map((cat, idx) => (
                  <div key={idx}>
                    <div className="flex items-center justify-between text-xs mb-1.5">
                      <span className="font-medium text-gray-300">{cat.category}</span>
                      <div className="flex items-center gap-2">
                        <span className={`text-[10px] px-1.5 py-0.5 rounded font-semibold ${
                          cat.status === 'Strong' ? 'bg-emerald-500/20 text-emerald-400' :
                          cat.status === 'Moderate' ? 'bg-amber-500/20 text-amber-400' : 'bg-rose-500/20 text-rose-400'
                        }`}>
                          {cat.status}
                        </span>
                        <span className="font-bold text-white">{cat.score}%</span>
                      </div>
                    </div>
                    <div className="w-full h-2 bg-gray-800 rounded-full overflow-hidden">
                      <div
                        className={`h-full rounded-full transition-all duration-700 ${
                          cat.score >= 75 ? 'bg-emerald-500' :
                          cat.score >= 50 ? 'bg-amber-500' : 'bg-rose-500'
                        }`}
                        style={{ width: `${cat.score}%` }}
                      />
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Matched Strengths vs Gaps (Separated Core vs Optional) */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {/* Matched Skills */}
            <div className="p-6 rounded-2xl bg-gray-950/60 border border-emerald-950/40">
              <div className="flex items-center gap-2 mb-3">
                <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                <h4 className="text-sm font-bold text-emerald-400">
                  Validated Strengths ({readinessData.matched_skills.length})
                </h4>
              </div>
              <div className="flex flex-wrap gap-2">
                {readinessData.matched_skills.length > 0 ? (
                  readinessData.matched_skills.map((skill, idx) => (
                    <span
                      key={idx}
                      className="px-2.5 py-1 rounded-md text-xs font-medium bg-emerald-950/50 text-emerald-300 border border-emerald-800/60"
                    >
                      ✓ {skill}
                    </span>
                  ))
                ) : (
                  <span className="text-xs text-gray-500">No verified skills yet.</span>
                )}
              </div>
            </div>

            {/* Core Gaps */}
            <div className="p-6 rounded-2xl bg-gray-950/60 border border-rose-950/40">
              <div className="flex items-center gap-2 mb-3">
                <AlertTriangle className="w-4 h-4 text-rose-400" />
                <h4 className="text-sm font-bold text-rose-400">
                  Critical Core Gaps ({coreGaps.length})
                </h4>
              </div>
              <div className="flex flex-wrap gap-2">
                {coreGaps.length > 0 ? (
                  coreGaps.map((skill, idx) => (
                    <span
                      key={idx}
                      className="px-2.5 py-1 rounded-md text-xs font-medium bg-rose-950/50 text-rose-300 border border-rose-800/60"
                    >
                      ! {skill}
                    </span>
                  ))
                ) : (
                  <span className="text-xs text-gray-500">All mandatory core skills satisfied!</span>
                )}
              </div>
            </div>

            {/* Optional / Elective Gaps */}
            <div className="p-6 rounded-2xl bg-gray-950/60 border border-indigo-950/40">
              <div className="flex items-center gap-2 mb-3">
                <Layers className="w-4 h-4 text-indigo-400" />
                <h4 className="text-sm font-bold text-indigo-400">
                  Elective Gaps ({optionalGaps.length})
                </h4>
              </div>
              <div className="flex flex-wrap gap-2">
                {optionalGaps.length > 0 ? (
                  optionalGaps.map((skill, idx) => (
                    <span
                      key={idx}
                      className="px-2.5 py-1 rounded-md text-xs font-medium bg-indigo-950/50 text-indigo-300 border border-indigo-800/60"
                    >
                      + {skill}
                    </span>
                  ))
                ) : (
                  <span className="text-xs text-gray-500">No optional gaps identified.</span>
                )}
              </div>
            </div>
          </div>

          {/* Strategic Recommendations & Learning Path CTA */}
          <div className="p-6 rounded-2xl bg-gray-950/80 border border-gray-800 flex flex-col md:flex-row items-start md:items-center justify-between gap-6">
            <div>
              <h4 className="text-sm font-bold text-white mb-2 flex items-center gap-2">
                <Compass className="w-4 h-4 text-emerald-400" />
                Strategic Career Advisory
              </h4>
              <ul className="text-xs text-gray-400 space-y-1.5 list-disc pl-4">
                {(readinessData.recommendations || []).map((rec, idx) => (
                  <li key={idx}>{rec}</li>
                ))}
              </ul>
            </div>

            <button
              onClick={onProceedToLearningPath}
              className="inline-flex items-center gap-2 px-6 py-3 rounded-xl bg-gradient-to-r from-emerald-600 to-teal-500 hover:from-emerald-500 hover:to-teal-400 text-white text-xs font-bold tracking-wide uppercase transition shadow-xl shadow-emerald-600/20 shrink-0"
            >
              <span>Generate Personalized Roadmap</span>
              <ArrowRight className="w-4 h-4" />
            </button>
          </div>

          {/* Historical Readiness Progression Timeline */}
          <div className="p-6 rounded-2xl bg-gray-950/70 border border-gray-800 space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <History className="w-4 h-4 text-blue-400" />
                <h4 className="text-sm font-bold text-white">
                  Readiness Score Progression History
                </h4>
              </div>
              <span className="text-xs text-gray-400">
                {historySnapshots.length} snapshot{historySnapshots.length === 1 ? '' : 's'} recorded
              </span>
            </div>

            {loadingHistory ? (
              <div className="flex items-center justify-center py-6 text-gray-500 text-xs">
                <Loader2 className="w-4 h-4 animate-spin mr-2" />
                <span>Loading authentic historical snapshots...</span>
              </div>
            ) : historySnapshots.length > 0 ? (
              <div className="space-y-3">
                {historySnapshots.map((snap, idx) => (
                  <div
                    key={snap.id || idx}
                    className="p-4 rounded-xl bg-gray-900 border border-gray-800 flex flex-col sm:flex-row sm:items-center justify-between gap-3"
                  >
                    <div className="flex items-center gap-3">
                      <div className="w-8 h-8 rounded-lg bg-gray-800 flex items-center justify-center text-xs font-bold text-gray-300">
                        #{idx + 1}
                      </div>
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="text-sm font-semibold text-white">{snap.target_role}</span>
                          <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold border ${getLevelBadge(snap.readiness_level)}`}>
                            {snap.readiness_level}
                          </span>
                        </div>
                        <div className="flex items-center gap-2 text-[11px] text-gray-400 mt-0.5">
                          <Calendar className="w-3 h-3" />
                          <span>{formatDate(snap.created_at)}</span>
                          <span>•</span>
                          <span>{snap.formula_version}</span>
                        </div>
                      </div>
                    </div>

                    <div className="flex items-center gap-4 self-end sm:self-center">
                      <div className="text-right">
                        <span className="text-lg font-black text-white">{snap.overall_readiness_score}%</span>
                        <div className="text-[10px] text-gray-400">
                          {snap.is_assessed ? `${snap.assessment_coverage_pct}% Verified` : 'Provisional Unassessed'}
                        </div>
                      </div>
                      <div className="w-24 h-2 bg-gray-800 rounded-full overflow-hidden hidden sm:block">
                        <div
                          className="h-full bg-emerald-500 rounded-full"
                          style={{ width: `${snap.overall_readiness_score}%` }}
                        />
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-xs text-gray-500 text-center py-4">
                No historical snapshots saved yet. Calculate readiness to record your baseline benchmark.
              </p>
            )}
          </div>
        </div>
      )}
    </section>
  );
}
