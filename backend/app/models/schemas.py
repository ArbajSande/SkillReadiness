from pydantic import BaseModel, EmailStr, Field
from typing import List, Optional, Dict, Any

# Health Schemas
class HealthResponse(BaseModel):
    status: str
    database: str
    engine: str
    timestamp: str
    version: str = "1.0.0"
    details: Optional[Dict[str, Any]] = None

# User & Auth Schemas
class UserRegister(BaseModel):
    email: EmailStr
    full_name: str = Field(..., min_length=2, max_length=100)
    password: str = Field(..., min_length=6, max_length=128)

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    id: str
    email: str
    full_name: str
    created_at: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse

# Resume & Skills Schemas
class SkillItem(BaseModel):
    name: str
    category: str # "Technical", "Frameworks & Libraries", "Databases & Cloud", "Soft Skills"
    proficiency_level: str # "Beginner", "Intermediate", "Advanced"
    confidence_score: float = 0.9
    source: Optional[str] = "resume_extracted"
    evidence_count: Optional[int] = 1

class ResumeUploadResponse(BaseModel):
    id: str
    user_id: str
    filename: str
    extracted_skills: List[SkillItem]
    total_skills: int
    raw_text_preview: str
    target_role: Optional[str] = None
    created_at: str

class SkillExtractRequest(BaseModel):
    text: str
    target_role: Optional[str] = "Full Stack Developer"

# Assessment Schemas
class AssessmentQuestion(BaseModel):
    id: str
    question: str
    options: List[str]
    skill: str
    difficulty: str

class AssessmentGenerateRequest(BaseModel):
    target_role: str = "Full Stack Developer"
    skills: Optional[List[str]] = None
    num_questions: int = 5
    difficulty_preference: Optional[str] = "balanced"

class AssessmentSessionResponse(BaseModel):
    assessment_id: str
    target_role: str
    questions: List[AssessmentQuestion]
    total_questions: int
    created_at: str

class AssessmentSubmitRequest(BaseModel):
    assessment_id: str
    answers: Dict[str, int] # question_id -> selected_option_index

class QuestionResult(BaseModel):
    question_id: str
    question: str
    skill: str
    selected_option: int
    correct_option: int
    is_correct: bool
    explanation: str
    difficulty: Optional[str] = "Intermediate"

class AssessmentResultResponse(BaseModel):
    assessment_id: str
    user_id: str
    target_role: str
    total_questions: int
    correct_answers: int
    score_percentage: float
    category_scores: Dict[str, float]
    demonstrated_skill_scores: Optional[Dict[str, float]] = None
    demonstrated_levels: Optional[Dict[str, str]] = None
    question_results: List[QuestionResult]
    completed_at: str

# Adaptive Assessment Interactive Schemas
class AdaptiveStartRequest(BaseModel):
    target_role: str = "Full Stack Developer"
    skills: Optional[List[str]] = None
    max_questions: int = 5

class AdaptiveStartResponse(BaseModel):
    assessment_id: str
    target_role: str
    question_number: int
    total_questions: int
    question: AssessmentQuestion
    is_completed: bool = False
    policy_version: str = "ADAPT-v1.0-baseline"
    created_at: str

class AdaptiveNextRequest(BaseModel):
    assessment_id: str
    question_id: str
    selected_option: int

class AdaptiveQuestionFeedback(BaseModel):
    question_id: str
    question: str
    skill: str
    selected_option: int
    correct_option: int
    is_correct: bool
    explanation: str
    difficulty: str

class AdaptiveNextResponse(BaseModel):
    assessment_id: str
    question_number: int
    total_questions: int
    feedback: AdaptiveQuestionFeedback
    next_question: Optional[AssessmentQuestion] = None
    is_completed: bool = False
    result: Optional[AssessmentResultResponse] = None
    policy_version: str = "ADAPT-v1.0-baseline"

# Readiness Schemas
class CategoryReadiness(BaseModel):
    category: str
    score: float # 0 - 100
    status: str # "Strong", "Moderate", "Needs Focus"

class SkillContribution(BaseModel):
    skill: str
    weight: float
    tier: str
    declared_level: Optional[str] = None
    assessed: bool
    demonstrated_score: Optional[float] = None
    effective_proficiency: float
    weighted_score: float
    max_possible: float
    gap: float
    status: str
    explanation: str

class ReadinessCalculateRequest(BaseModel):
    target_role: str = "Full Stack Developer"
    resume_id: Optional[str] = None
    assessment_id: Optional[str] = None

class ReadinessResultResponse(BaseModel):
    id: str
    user_id: str
    target_role: str
    overall_readiness_score: float # 0 - 100
    readiness_level: str # "Job Ready", "Near Ready", "Intermediate", "Needs Upskilling"
    category_breakdown: List[CategoryReadiness]
    matched_skills: List[str]
    gap_skills: List[str]
    critical_core_gaps: Optional[List[str]] = None
    optional_gaps: Optional[List[str]] = None
    recommendations: List[str]
    formula_version: str = "SR-v2.0-baseline"
    is_assessed: bool = False
    assessment_coverage_pct: float = 0.0
    skill_contributions: Optional[List[Dict[str, Any]]] = None
    created_at: str

# Readiness Historical Tracking Schemas
class ReadinessHistoryItem(BaseModel):
    id: str
    target_role: str
    overall_readiness_score: float
    readiness_level: str
    formula_version: str = "SR-v2.0-baseline"
    is_assessed: bool = False
    assessment_coverage_pct: float = 0.0
    critical_core_gaps: List[str] = []
    optional_gaps: List[str] = []
    created_at: str

class ReadinessHistoryResponse(BaseModel):
    user_id: str
    snapshots_count: int
    snapshots: List[ReadinessHistoryItem]

# Learning Path Schemas
class LearningModuleItem(BaseModel):
    id: str
    title: str
    description: str
    resource_url: str
    duration_hours: int
    completed: bool = False
    prerequisites: Optional[List[str]] = None
    recommendation_reason: Optional[str] = None

class LearningMilestone(BaseModel):
    week: int
    title: str
    focus_skills: List[str]
    items: List[LearningModuleItem]

class LearningPathResponse(BaseModel):
    id: str
    user_id: str
    target_role: str
    overall_progress_percentage: float
    total_items: int
    completed_items: int
    milestones: List[LearningMilestone]
    updated_at: str

class LearningProgressUpdateRequest(BaseModel):
    item_id: str
    completed: bool
