import React, { useState, useEffect, useRef } from 'react';
import Navbar from './components/Navbar';
import AuthModal from './components/AuthModal';
import ResumeUploadSection from './components/ResumeUploadSection';
import AssessmentSection from './components/AssessmentSection';
import ReadinessDashboard from './components/ReadinessDashboard';
import LearningPathSection from './components/LearningPathSection';
import { api } from './api/client';
import { Sparkles, Brain, CheckCircle2, ArrowDownCircle, ShieldCheck } from 'lucide-react';

export default function App() {
  const [user, setUser] = useState(null);
  const [authModalOpen, setAuthModalOpen] = useState(false);
  const [healthStatus, setHealthStatus] = useState({ connected: false, checked: false });

  // Core application workflow state
  const [targetRole, setTargetRole] = useState("Full Stack Developer");
  const [extractedSkills, setExtractedSkills] = useState([]);
  const [resumeId, setResumeId] = useState(null);
  const [assessmentId, setAssessmentId] = useState(null);
  const [assessmentResult, setAssessmentResult] = useState(null);
  const [readinessData, setReadinessData] = useState(null);
  const [learningPath, setLearningPath] = useState(null);

  // Section Refs for smooth scrolling
  const assessmentRef = useRef(null);
  const readinessRef = useRef(null);
  const learningPathRef = useRef(null);

  // 1. Initial health and auth check on load
  useEffect(() => {
    async function init() {
      // Check API Health
      try {
        const health = await api.checkHealth();
        setHealthStatus({
          connected: health.status === 'ok' && health.database === 'connected',
          checked: true,
        });
      } catch (err) {
        setHealthStatus({ connected: false, checked: true });
      }

      // Check User Authentication
      const token = localStorage.getItem('sr_token');
      if (token) {
        try {
          const profile = await api.getMe();
          setUser(profile);
        } catch (err) {
          localStorage.removeItem('sr_token');
          setUser(null);
        }
      }
    }
    init();
  }, []);

  function handleLogout() {
    localStorage.removeItem('sr_token');
    setUser(null);
  }

  function handleProceedToAssessment() {
    assessmentRef.current?.scrollIntoView({ behavior: 'smooth' });
  }

  function handleProceedToReadiness() {
    readinessRef.current?.scrollIntoView({ behavior: 'smooth' });
  }

  function handleProceedToLearningPath() {
    learningPathRef.current?.scrollIntoView({ behavior: 'smooth' });
  }

  return (
    <div className="min-h-screen bg-[#090d16] text-gray-100 flex flex-col selection:bg-emerald-500/30">
      {/* Navigation */}
      <Navbar
        user={user}
        onOpenAuth={() => setAuthModalOpen(true)}
        onLogout={handleLogout}
        healthStatus={healthStatus}
      />

      {/* Hero Header */}
      <main className="flex-1 max-w-6xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8 sm:py-12">
        <section className="text-center max-w-3xl mx-auto mb-10 sm:mb-14">
          <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 mb-4 shadow-sm shadow-emerald-500/10">
            <Sparkles className="w-3.5 h-3.5" />
            <span>AI-Powered Career Intelligence & Readiness Assessment</span>
          </div>

          <h1 className="text-3xl sm:text-5xl font-black text-white tracking-tight mb-4 leading-tight sm:leading-tight">
            Bridge the Gap to Your <br className="hidden sm:inline" />
            <span className="bg-gradient-to-r from-emerald-400 via-teal-300 to-cyan-400 bg-clip-text text-transparent">
              Target Engineering Role
            </span>
          </h1>

          <p className="text-sm sm:text-base text-gray-400 leading-relaxed mb-6">
            Upload your resume, verify your competencies through dynamic assessments, calculate your exact readiness score against industry benchmarks, and follow a personalized learning path.
          </p>

          {/* Value Props Pills */}
          <div className="flex flex-wrap items-center justify-center gap-3 text-xs text-gray-300 font-medium">
            <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-gray-900 border border-gray-800">
              <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" /> Automated NLP Extraction
            </span>
            <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-gray-900 border border-gray-800">
              <Brain className="w-3.5 h-3.5 text-teal-400" /> Dynamic Adaptive Quizzing
            </span>
            <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-gray-900 border border-gray-800">
              <ShieldCheck className="w-3.5 h-3.5 text-blue-400" /> Persistent MongoDB Tracking
            </span>
          </div>
        </section>

        {/* Step 1: Intake & Resume Upload */}
        <ResumeUploadSection
          targetRole={targetRole}
          setTargetRole={setTargetRole}
          extractedSkills={extractedSkills}
          setExtractedSkills={setExtractedSkills}
          resumeId={resumeId}
          setResumeId={setResumeId}
          onProceedToAssessment={handleProceedToAssessment}
        />

        {/* Step 2: Assessment Quiz */}
        <div ref={assessmentRef}>
          <AssessmentSection
            targetRole={targetRole}
            extractedSkills={extractedSkills}
            assessmentId={assessmentId}
            setAssessmentId={setAssessmentId}
            assessmentResult={assessmentResult}
            setAssessmentResult={setAssessmentResult}
            onProceedToReadiness={handleProceedToReadiness}
          />
        </div>

        {/* Step 3: Readiness Analytics */}
        <div ref={readinessRef}>
          <ReadinessDashboard
            targetRole={targetRole}
            resumeId={resumeId}
            assessmentId={assessmentId}
            readinessData={readinessData}
            setReadinessData={setReadinessData}
            onProceedToLearningPath={handleProceedToLearningPath}
          />
        </div>

        {/* Step 4: Customized Learning Roadmap */}
        <div ref={learningPathRef}>
          <LearningPathSection
            targetRole={targetRole}
            learningPath={learningPath}
            setLearningPath={setLearningPath}
          />
        </div>
      </main>

      {/* Footer */}
      <footer className="border-t border-gray-900 bg-gray-950/60 py-6 text-center text-xs text-gray-500">
        SkillReadiness AI • Production Audited • Powered by FastAPI, React & MongoDB
      </footer>

      {/* Auth Modal */}
      <AuthModal
        isOpen={authModalOpen}
        onClose={() => setAuthModalOpen(false)}
        onAuthSuccess={(userData) => setUser(userData)}
      />
    </div>
  );
}
