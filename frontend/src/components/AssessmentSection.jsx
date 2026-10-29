import React, { useState } from 'react';
import {
  HelpCircle,
  CheckCircle,
  XCircle,
  ArrowRight,
  Loader2,
  Sparkles,
  AlertCircle,
  Award,
  RefreshCw,
  TrendingUp,
  BrainCircuit,
  ChevronRight
} from 'lucide-react';
import { api } from '../api/client';

export default function AssessmentSection({
  targetRole,
  extractedSkills,
  assessmentId,
  setAssessmentId,
  assessmentResult,
  setAssessmentResult,
  onProceedToReadiness
}) {
  // Adaptive session state
  const [currentQuestion, setCurrentQuestion] = useState(null);
  const [questionNumber, setQuestionNumber] = useState(0);
  const [totalQuestions, setTotalQuestions] = useState(5);
  const [selectedOption, setSelectedOption] = useState(null);
  const [questionFeedback, setQuestionFeedback] = useState(null);
  const [pendingNextQuestion, setPendingNextQuestion] = useState(null);
  const [pendingResult, setPendingResult] = useState(null);
  const [feedbackHistory, setFeedbackHistory] = useState([]);

  // UI state
  const [loading, setLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);

  // Difficulty badge colors
  function getDifficultyBadge(diff) {
    switch (diff) {
      case 'Beginner':
        return 'bg-blue-500/15 text-blue-400 border-blue-500/30';
      case 'Intermediate':
        return 'bg-amber-500/15 text-amber-400 border-amber-500/30';
      case 'Advanced':
        return 'bg-purple-500/15 text-purple-400 border-purple-500/30';
      default:
        return 'bg-gray-800 text-gray-400 border-gray-700';
    }
  }

  // 1. Start adaptive assessment
  async function handleStartAdaptiveAssessment() {
    setError(null);
    setLoading(true);
    setAssessmentResult(null);
    setQuestionFeedback(null);
    setPendingNextQuestion(null);
    setPendingResult(null);
    setSelectedOption(null);
    setFeedbackHistory([]);

    try {
      const skillNames = (extractedSkills || []).map(s => s.name);
      const res = await api.startAdaptiveAssessment(targetRole, skillNames, 5);
      setAssessmentId(res.assessment_id);
      setCurrentQuestion(res.question);
      setQuestionNumber(res.question_number);
      setTotalQuestions(res.total_questions);
    } catch (err) {
      setError(err.message || 'Failed to start adaptive assessment.');
    } finally {
      setLoading(false);
    }
  }

  // 2. Submit current question answer for server grading & adaptation
  async function handleSubmitCurrentAnswer() {
    if (selectedOption === null || !currentQuestion || !assessmentId) return;

    setError(null);
    setSubmitting(true);

    try {
      const res = await api.submitAdaptiveNext(
        assessmentId,
        currentQuestion.id,
        selectedOption
      );

      setQuestionFeedback(res.feedback);
      setFeedbackHistory(prev => [...prev, res.feedback]);

      if (res.is_completed) {
        setPendingNextQuestion(null);
        setPendingResult(res.result);
      } else {
        setPendingNextQuestion(res.next_question);
        setPendingResult(null);
      }
    } catch (err) {
      setError(err.message || 'Failed to grade answer. Please check connection and try again.');
    } finally {
      setSubmitting(false);
    }
  }

  // 3. Move to next question or complete session
  function handleAdvanceQuestion() {
    if (pendingResult) {
      setAssessmentResult(pendingResult);
      setCurrentQuestion(null);
      setQuestionFeedback(null);
      setPendingResult(null);
    } else if (pendingNextQuestion) {
      setCurrentQuestion(pendingNextQuestion);
      setQuestionNumber(prev => prev + 1);
      setSelectedOption(null);
      setQuestionFeedback(null);
      setPendingNextQuestion(null);
    }
  }

  const progressPct = totalQuestions > 0 ? Math.round(((questionNumber - 1) / totalQuestions) * 100) : 0;

  return (
    <section className="bg-gray-900/60 border border-gray-800 rounded-2xl p-6 sm:p-8 backdrop-blur mt-8">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-6">
        <div>
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-semibold bg-blue-500/10 text-blue-400 border border-blue-500/20 mb-2">
            <BrainCircuit className="w-3.5 h-3.5" />
            Step 2: Interactive Adaptive Assessment (ADAPT-v1.0-baseline)
          </div>
          <h2 className="text-xl font-bold text-white tracking-tight">Adaptive Skill Verification Engine</h2>
          <p className="text-sm text-gray-400">
            One-question-at-a-time testing: questions dynamically adapt difficulty based on real-time answer accuracy.
          </p>
        </div>

        {!currentQuestion && !assessmentResult && (
          <button
            onClick={handleStartAdaptiveAssessment}
            disabled={loading}
            className="inline-flex items-center gap-2 px-6 py-2.5 rounded-lg bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white text-sm font-semibold transition shadow-lg shadow-blue-600/20 shrink-0"
          >
            {loading ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                <span>Initializing Engine...</span>
              </>
            ) : (
              <>
                <Sparkles className="w-4 h-4" />
                <span>Start Adaptive Quiz</span>
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

      {/* Active Question View */}
      {currentQuestion && !assessmentResult && (
        <div className="space-y-6 animate-fade-in">
          {/* Progress Bar & Difficulty Tag */}
          <div className="p-4 rounded-xl bg-gray-950/80 border border-gray-800 space-y-3">
            <div className="flex items-center justify-between text-xs">
              <span className="font-semibold text-gray-300">
                Question {questionNumber} of {totalQuestions}
              </span>
              <div className="flex items-center gap-2">
                <span className="text-gray-400">Target Skill: <strong className="text-white">{currentQuestion.skill}</strong></span>
                <span className={`px-2.5 py-0.5 rounded-full text-[11px] font-bold border ${getDifficultyBadge(currentQuestion.difficulty)}`}>
                  {currentQuestion.difficulty}
                </span>
              </div>
            </div>

            <div className="w-full h-2 bg-gray-800 rounded-full overflow-hidden">
              <div
                className="h-full bg-gradient-to-r from-blue-500 to-indigo-500 rounded-full transition-all duration-500"
                style={{ width: `${Math.max(10, progressPct)}%` }}
              />
            </div>
          </div>

          {/* Question Statement */}
          <div className="p-6 rounded-xl bg-gray-950/60 border border-gray-800">
            <p className="text-base sm:text-lg font-medium text-white mb-6 leading-relaxed">
              {currentQuestion.question}
            </p>

            {/* Multiple Choice Options */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              {currentQuestion.options.map((opt, optIdx) => {
                const isSelected = selectedOption === optIdx;
                const isLocked = questionFeedback !== null;
                const isCorrectOption = questionFeedback && questionFeedback.correct_option === optIdx;
                const isWrongSelection = questionFeedback && !questionFeedback.is_correct && isSelected;

                let cardStyle = 'border-gray-800 bg-gray-900/40 text-gray-300 hover:border-gray-700 hover:bg-gray-900';
                if (isSelected && !isLocked) {
                  cardStyle = 'border-blue-500 bg-blue-500/15 text-white font-medium shadow-md shadow-blue-500/10';
                } else if (isLocked) {
                  if (isCorrectOption) {
                    cardStyle = 'border-emerald-500 bg-emerald-500/15 text-emerald-200 font-medium';
                  } else if (isWrongSelection) {
                    cardStyle = 'border-rose-500 bg-rose-500/15 text-rose-200';
                  } else {
                    cardStyle = 'border-gray-800/40 bg-gray-950/40 text-gray-500 opacity-60';
                  }
                }

                return (
                  <button
                    type="button"
                    key={optIdx}
                    disabled={isLocked}
                    onClick={() => setSelectedOption(optIdx)}
                    className={`text-left p-4 rounded-xl border text-sm transition flex items-start gap-3 ${cardStyle}`}
                  >
                    <span className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold shrink-0 mt-0.5 ${
                      isSelected && !isLocked ? 'bg-blue-500 text-gray-950' : 'bg-gray-800 text-gray-400'
                    }`}>
                      {String.fromCharCode(65 + optIdx)}
                    </span>
                    <span className="leading-snug">{opt}</span>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Immediate Server-Side Feedback Banner */}
          {questionFeedback && (
            <div className={`p-5 rounded-xl border animate-fade-in ${
              questionFeedback.is_correct
                ? 'bg-emerald-950/20 border-emerald-500/40 text-emerald-300'
                : 'bg-rose-950/20 border-rose-500/40 text-rose-300'
            }`}>
              <div className="flex items-center gap-2 mb-2 font-bold text-sm">
                {questionFeedback.is_correct ? (
                  <>
                    <CheckCircle className="w-5 h-5 text-emerald-400" />
                    <span className="text-emerald-400">Correct! Adaptive engine stepping up difficulty.</span>
                  </>
                ) : (
                  <>
                    <XCircle className="w-5 h-5 text-rose-400" />
                    <span className="text-rose-400">Incorrect. Adaptive engine adjusting to foundational concepts.</span>
                  </>
                )}
              </div>
              <p className="text-xs text-gray-300 leading-relaxed bg-gray-950/60 p-3 rounded-lg border border-gray-800/80">
                <strong className="text-white">Explanation: </strong>
                {questionFeedback.explanation}
              </p>
            </div>
          )}

          {/* Action Button Footer */}
          <div className="flex items-center justify-between pt-4 border-t border-gray-800">
            <span className="text-xs text-gray-400">
              {questionFeedback ? "Review the explanation above and advance." : "Select an option and verify."}
            </span>

            {!questionFeedback ? (
              <button
                type="button"
                onClick={handleSubmitCurrentAnswer}
                disabled={selectedOption === null || submitting}
                className="px-6 py-2.5 rounded-lg bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white text-sm font-semibold transition flex items-center gap-2 shadow-lg shadow-blue-600/20"
              >
                {submitting ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    <span>Grading on Backend...</span>
                  </>
                ) : (
                  <span>Submit & Verify</span>
                )}
              </button>
            ) : (
              <button
                type="button"
                onClick={handleAdvanceQuestion}
                className="px-6 py-2.5 rounded-lg bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white text-sm font-semibold transition flex items-center gap-2 shadow-lg shadow-blue-600/20"
              >
                <span>{pendingResult ? "View Final Assessment Results" : "Next Adaptive Question"}</span>
                <ChevronRight className="w-4 h-4" />
              </button>
            )}
          </div>
        </div>
      )}

      {/* Final Assessment Scorecard & Results Review */}
      {assessmentResult && (
        <div className="animate-fade-in space-y-6">
          {/* Top Score Banner */}
          <div className="p-6 rounded-2xl bg-gradient-to-r from-blue-950/40 via-indigo-950/40 to-gray-950 border border-blue-800/40 flex flex-col md:flex-row items-center justify-between gap-6">
            <div className="flex items-center gap-4">
              <div className="w-16 h-16 rounded-2xl bg-blue-500/20 border border-blue-500/30 flex items-center justify-center text-blue-400">
                <Award className="w-8 h-8" />
              </div>
              <div>
                <span className="text-xs uppercase tracking-wider font-semibold text-blue-400">Adaptive Scorecard</span>
                <h3 className="text-2xl font-black text-white">
                  {assessmentResult.score_percentage}% Overall Accuracy
                </h3>
                <p className="text-xs text-gray-400">
                  {assessmentResult.correct_answers} of {assessmentResult.total_questions} questions answered correctly
                </p>
              </div>
            </div>

            <div className="flex items-center gap-3">
              <button
                onClick={handleStartAdaptiveAssessment}
                className="px-4 py-2 rounded-lg bg-gray-800 hover:bg-gray-700 text-gray-300 text-xs font-semibold transition flex items-center gap-1.5"
              >
                <RefreshCw className="w-3.5 h-3.5" />
                <span>Retake Assessment</span>
              </button>
              <button
                onClick={onProceedToReadiness}
                className="inline-flex items-center gap-2 px-5 py-2.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold tracking-wide uppercase transition shadow-md shadow-emerald-600/20"
              >
                <span>Calculate Overall Readiness</span>
                <ArrowRight className="w-4 h-4" />
              </button>
            </div>
          </div>

          {/* Demonstrated Skill Competencies */}
          {assessmentResult.demonstrated_levels && Object.keys(assessmentResult.demonstrated_levels).length > 0 && (
            <div className="p-5 rounded-xl bg-gray-950/70 border border-gray-800">
              <h4 className="text-xs font-bold text-gray-400 uppercase tracking-wider mb-3">
                Demonstrated Skill Breakdown
              </h4>
              <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-3">
                {Object.entries(assessmentResult.demonstrated_levels).map(([skill, level]) => (
                  <div key={skill} className="p-3 rounded-lg bg-gray-900 border border-gray-800">
                    <span className="text-xs font-medium text-gray-300 block truncate">{skill}</span>
                    <span className={`text-[11px] font-bold mt-1 inline-block ${
                      level === 'Advanced' ? 'text-emerald-400' :
                      level === 'Intermediate' ? 'text-amber-400' : 'text-rose-400'
                    }`}>
                      {level} ({Math.round((assessmentResult.demonstrated_skill_scores?.[skill] || 0) * 100)}%)
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Detailed Question Review */}
          <div className="space-y-4">
            <h4 className="text-sm font-semibold text-gray-300">Answer Review & Concepts</h4>
            {assessmentResult.question_results.map((qr, idx) => (
              <div
                key={qr.question_id || idx}
                className={`p-4 rounded-xl border ${
                  qr.is_correct ? 'bg-emerald-950/20 border-emerald-800/40' : 'bg-rose-950/20 border-rose-800/40'
                }`}
              >
                <div className="flex items-center justify-between mb-2">
                  <span className="text-xs font-bold text-gray-400">
                    Question {idx + 1} • {qr.skill} ({qr.difficulty || 'Intermediate'})
                  </span>
                  <span className={`text-xs font-semibold flex items-center gap-1.5 ${
                    qr.is_correct ? 'text-emerald-400' : 'text-rose-400'
                  }`}>
                    {qr.is_correct ? <CheckCircle className="w-4 h-4" /> : <XCircle className="w-4 h-4" />}
                    {qr.is_correct ? 'Correct' : 'Incorrect'}
                  </span>
                </div>
                <p className="text-sm font-medium text-white mb-2">{qr.question}</p>
                <p className="text-xs text-gray-400 bg-gray-950/60 p-2.5 rounded-lg border border-gray-800/60">
                  <strong className="text-gray-300 font-semibold">Concept Explanation: </strong>
                  {qr.explanation}
                </p>
              </div>
            ))}
          </div>
        </div>
      )}
    </section>
  );
}
