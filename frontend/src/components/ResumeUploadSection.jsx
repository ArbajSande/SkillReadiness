import React, { useState } from 'react';
import { UploadCloud, FileText, CheckCircle2, Loader2, Sparkles, AlertCircle, ArrowRight } from 'lucide-react';
import { api } from '../api/client';

const TARGET_ROLES = [
  "Full Stack Developer",
  "Frontend Developer",
  "Backend Developer",
  "Data Scientist / AI Engineer",
  "DevOps / Cloud Engineer"
];

export default function ResumeUploadSection({
  targetRole,
  setTargetRole,
  extractedSkills,
  setExtractedSkills,
  resumeId,
  setResumeId,
  onProceedToAssessment
}) {
  const [activeTab, setActiveTab] = useState('file'); // 'file' or 'text'
  const [selectedFile, setSelectedFile] = useState(null);
  const [rawText, setRawText] = useState('');
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState(null);
  const [uploadSuccess, setUploadSuccess] = useState(false);

  async function handleUpload(e) {
    e.preventDefault();
    setError(null);
    setUploadSuccess(false);
    setUploading(true);

    try {
      const formData = new FormData();
      formData.append('target_role', targetRole);

      if (activeTab === 'file') {
        if (!selectedFile) {
          throw new Error('Please select a resume file (PDF, DOCX, or TXT).');
        }
        formData.append('file', selectedFile);
      } else {
        if (!rawText.trim() || rawText.trim().length < 20) {
          throw new Error('Please paste at least a brief summary of your skills, experience, or resume text.');
        }
        formData.append('text_content', rawText.trim());
      }

      const res = await api.uploadResume(formData);
      setResumeId(res.id);
      setExtractedSkills(res.extracted_skills || []);
      setUploadSuccess(true);
    } catch (err) {
      setError(err.message || 'Failed to parse resume document.');
    } finally {
      setUploading(false);
    }
  }

  // Pre-fill sample resume for quick 1-click test
  function handleUseSampleResume() {
    setActiveTab('text');
    setRawText(`Full Stack Software Engineer with 3+ years of experience building modern web architectures.
Proficient in Python, FastAPI, React, Node.js, and TypeScript.
Hands-on experience deploying containerized services with Docker, Kubernetes, and AWS.
Worked with MongoDB and PostgreSQL databases, Redis caching, and REST API development.
Practiced Agile methodologies, system design fundamentals, and team collaboration.`);
  }

  // Group extracted skills by category
  const skillsByCategory = (extractedSkills || []).reduce((acc, skill) => {
    const cat = skill.category || 'Other';
    if (!acc[cat]) acc[cat] = [];
    acc[cat].push(skill);
    return acc;
  }, {});

  return (
    <section className="bg-gray-900/60 border border-gray-800 rounded-2xl p-6 sm:p-8 backdrop-blur">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-6">
        <div>
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 mb-2">
            Step 1: Role & Skills Intake
          </div>
          <h2 className="text-xl font-bold text-white tracking-tight">Select Career Target & Ingest Resume</h2>
          <p className="text-sm text-gray-400">Our NLP engine parses your technical background to evaluate role alignment.</p>
        </div>

        {/* Target Role Selector */}
        <div className="w-full md:w-64">
          <label className="block text-xs font-medium text-gray-400 mb-1.5">Target Benchmark Role</label>
          <select
            value={targetRole}
            onChange={(e) => setTargetRole(e.target.value)}
            className="w-full px-3 py-2 bg-gray-950 border border-gray-800 rounded-lg text-sm text-white focus:outline-none focus:border-emerald-500 font-medium"
          >
            {TARGET_ROLES.map((role) => (
              <option key={role} value={role}>{role}</option>
            ))}
          </select>
        </div>
      </div>

      {error && (
        <div className="mb-6 p-4 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-400 text-sm flex items-center gap-3">
          <AlertCircle className="w-5 h-5 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Tabs: Upload File vs Paste Text */}
      <div className="flex items-center justify-between border-b border-gray-800 mb-4">
        <div className="flex gap-4">
          <button
            type="button"
            onClick={() => setActiveTab('file')}
            className={`pb-3 text-sm font-semibold border-b-2 transition ${
              activeTab === 'file'
                ? 'border-emerald-500 text-emerald-400'
                : 'border-transparent text-gray-400 hover:text-gray-200'
            }`}
          >
            Upload Resume (PDF / DOCX / TXT)
          </button>
          <button
            type="button"
            onClick={() => setActiveTab('text')}
            className={`pb-3 text-sm font-semibold border-b-2 transition ${
              activeTab === 'text'
                ? 'border-emerald-500 text-emerald-400'
                : 'border-transparent text-gray-400 hover:text-gray-200'
            }`}
          >
            Paste Text or Profile
          </button>
        </div>

        <button
          type="button"
          onClick={handleUseSampleResume}
          className="text-xs text-emerald-400 hover:text-emerald-300 font-medium pb-3 hover:underline"
        >
          Load Demo Engineer Resume
        </button>
      </div>

      <form onSubmit={handleUpload}>
        {activeTab === 'file' ? (
          <div className="border-2 border-dashed border-gray-800 hover:border-gray-700 rounded-2xl p-8 text-center transition bg-gray-950/40">
            <UploadCloud className="w-12 h-12 text-gray-500 mx-auto mb-3" />
            <p className="text-sm text-gray-300 font-medium mb-1">
              {selectedFile ? selectedFile.name : 'Click to select or drag and drop your resume'}
            </p>
            <p className="text-xs text-gray-500 mb-4">Supports .pdf, .docx, and .txt up to 10MB</p>
            <input
              type="file"
              id="resume-file"
              accept=".pdf,.docx,.doc,.txt"
              onChange={(e) => setSelectedFile(e.target.files[0] || null)}
              className="hidden"
            />
            <label
              htmlFor="resume-file"
              className="inline-block px-4 py-2 bg-gray-800 hover:bg-gray-700 text-white text-xs font-semibold rounded-lg cursor-pointer transition border border-gray-700"
            >
              Browse Local Document
            </label>
          </div>
        ) : (
          <div>
            <textarea
              rows={6}
              value={rawText}
              onChange={(e) => setRawText(e.target.value)}
              placeholder="Paste your raw resume summary, technical skills section, or project highlights here..."
              className="w-full p-4 bg-gray-950 border border-gray-800 rounded-xl text-sm text-white focus:outline-none focus:border-emerald-500 font-mono"
            />
          </div>
        )}

        <div className="mt-4 flex items-center justify-end">
          <button
            type="submit"
            disabled={uploading}
            className="px-6 py-2.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white text-sm font-semibold transition flex items-center gap-2 shadow-lg shadow-emerald-600/20"
          >
            {uploading ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                <span>Extracting Skills with NLP...</span>
              </>
            ) : (
              <>
                <Sparkles className="w-4 h-4" />
                <span>Extract & Parse Skills</span>
              </>
            )}
          </button>
        </div>
      </form>

      {/* Extracted Skills Visualization */}
      {extractedSkills && extractedSkills.length > 0 && (
        <div className="mt-8 pt-6 border-t border-gray-800 animate-fade-in">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <CheckCircle2 className="w-5 h-5 text-emerald-400" />
              <h3 className="text-base font-semibold text-white">
                Extracted Skills ({extractedSkills.length} Identified)
              </h3>
            </div>
            <button
              onClick={onProceedToAssessment}
              className="inline-flex items-center gap-2 px-5 py-2 rounded-lg bg-teal-600 hover:bg-teal-500 text-white text-xs font-semibold tracking-wide uppercase transition shadow-md shadow-teal-600/20"
            >
              <span>Take Skill Assessment</span>
              <ArrowRight className="w-4 h-4" />
            </button>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {Object.entries(skillsByCategory).map(([category, skills]) => (
              <div key={category} className="p-4 rounded-xl bg-gray-950/60 border border-gray-800/80">
                <span className="text-xs font-semibold uppercase tracking-wider text-gray-400 block mb-2.5">
                  {category}
                </span>
                <div className="flex flex-wrap gap-2">
                  {skills.map((skill, idx) => (
                    <span
                      key={idx}
                      className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-medium bg-gray-800 text-gray-200 border border-gray-700/80"
                    >
                      <span>{skill.name}</span>
                      <span className="text-[10px] px-1 rounded bg-emerald-500/20 text-emerald-300">
                        {skill.proficiency_level}
                      </span>
                    </span>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </section>
  );
}
