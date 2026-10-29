const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

function getAuthHeader() {
  const token = localStorage.getItem('sr_token');
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function request(endpoint, options = {}) {
  const url = `${API_BASE}${endpoint}`;
  const headers = {
    ...getAuthHeader(),
    ...(options.headers || {}),
  };

  const response = await fetch(url, {
    ...options,
    headers,
  });

  const contentType = response.headers.get('content-type');
  const isJson = contentType && contentType.includes('application/json');
  const data = isJson ? await response.json() : await response.text();

  if (!response.ok) {
    const errorMsg = data && data.detail ? data.detail : `Request failed with status ${response.status}`;
    throw new Error(errorMsg);
  }

  return data;
}

export const api = {
  // Health
  checkHealth: () => request('/health'),

  // Auth
  register: (email, fullName, password) =>
    request('/api/auth/register', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, full_name: fullName, password }),
    }),

  login: (email, password) =>
    request('/api/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password }),
    }),

  getMe: () => request('/api/auth/me'),

  // Resume & Skills
  uploadResume: (formData) =>
    request('/api/resume/upload', {
      method: 'POST',
      body: formData, // FormData automatically handles Content-Type multipart
    }),

  extractSkillsRaw: (text, targetRole) =>
    request('/api/resume/extract-skills', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text, target_role: targetRole }),
    }),

  getLatestResume: () => request('/api/resume/latest'),

  // Assessment
  generateAssessment: (targetRole, skills = [], numQuestions = 5) =>
    request('/api/assessment/generate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        target_role: targetRole,
        skills,
        num_questions: numQuestions,
      }),
    }),

  submitAssessment: (assessmentId, answers) =>
    request('/api/assessment/submit', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        assessment_id: assessmentId,
        answers,
      }),
    }),

  // Interactive Adaptive Assessment (One-question-at-a-time)
  startAdaptiveAssessment: (targetRole, skills = [], maxQuestions = 5) =>
    request('/api/assessment/adaptive/start', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        target_role: targetRole,
        skills,
        max_questions: maxQuestions,
      }),
    }),

  submitAdaptiveNext: (assessmentId, questionId, selectedOption) =>
    request('/api/assessment/adaptive/next', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        assessment_id: assessmentId,
        question_id: questionId,
        selected_option: selectedOption,
      }),
    }),

  getAdaptiveStatus: (assessmentId) =>
    request(`/api/assessment/adaptive/${assessmentId}`),

  // Readiness
  calculateReadiness: (targetRole, resumeId = null, assessmentId = null) =>
    request('/api/readiness/calculate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        target_role: targetRole,
        resume_id: resumeId,
        assessment_id: assessmentId,
      }),
    }),

  getLatestReadiness: () => request('/api/readiness/latest'),

  getReadinessHistory: () => request('/api/readiness/history'),

  // Learning Path
  generateLearningPath: (targetRole) =>
    request(`/api/learning-path/generate?target_role=${encodeURIComponent(targetRole)}`, {
      method: 'POST',
    }),

  getCurrentLearningPath: () => request('/api/learning-path/current'),

  updateProgress: (itemId, completed) =>
    request('/api/learning-path/progress', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        item_id: itemId,
        completed,
      }),
    }),
};
