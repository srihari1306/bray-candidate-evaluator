"""
Pydantic schemas for request/response models.
All API contracts are defined here with full type safety.
"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from enum import Enum


# ─── Enums ───────────────────────────────────────────────────────────────────

class RecommendationType(str, Enum):
    STRONG_MATCH = "Strong Match"
    GOOD_MATCH = "Good Match"
    MODERATE_MATCH = "Moderate Match"
    WEAK_MATCH = "Weak Match"
    NOT_RECOMMENDED = "Not Recommended"


class ConfidenceLevel(str, Enum):
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"


class EvaluationStatus(str, Enum):
    PENDING = "pending"
    FETCHING_RESUMES = "fetching_resumes"
    PARSING = "parsing"
    EMBEDDING = "embedding"
    INDEXING = "indexing"
    EVALUATING = "evaluating"
    COMPLETED = "completed"
    FAILED = "failed"


# ─── Request Models ─────────────────────────────────────────────────────────

class SkillCategory(BaseModel):
    """A custom skill category with optional weight."""
    name: str = Field(..., description="Skill category name, e.g. 'Cloud Engineering'")
    weight: int = Field(default=0, ge=0, le=100, description="Weight percentage (0-100)")


class EvaluationRequest(BaseModel):
    """Request to evaluate candidates against a job description."""
    job_description: str = Field(..., min_length=50, description="Full job description text")
    job_title: str = Field(default="", description="Job title for reference")
    skills: list[SkillCategory] = Field(default_factory=list, description="Custom skill categories")
    max_candidates: int = Field(default=50, ge=1, le=200)
    reindex: bool = Field(default=False, description="Force re-fetch from SharePoint")

    class Config:
        json_schema_extra = {
            "example": {
                "job_description": "We are looking for an AI Engineer with strong experience in cloud infrastructure, agentic AI systems, and Linux/terminal proficiency...",
                "job_title": "Senior AI Engineer",
                "skills": [
                    {"name": "Cloud Engineering", "weight": 40},
                    {"name": "Agentic AI", "weight": 35},
                    {"name": "Terminal/Linux", "weight": 25}
                ],
                "max_candidates": 50,
                "reindex": False
            }
        }


class ShortlistRequest(BaseModel):
    """Request to toggle candidate shortlist status."""
    shortlisted: bool = True


class NoteRequest(BaseModel):
    """Request to add a recruiter note to a candidate."""
    content: str = Field(..., min_length=1, max_length=2000)


# ─── Response Models ────────────────────────────────────────────────────────

class SkillScore(BaseModel):
    """Score for a specific skill category."""
    skill: str
    score: int = Field(ge=0, le=100)
    confidence: ConfidenceLevel
    evidence: list[str] = Field(default_factory=list)


class ParsedProfile(BaseModel):
    """Structured data extracted from a resume."""
    name: str = ""
    email: str = ""
    phone: str = ""
    skills: list[str] = Field(default_factory=list)
    experience_years: Optional[float] = None
    education: list[str] = Field(default_factory=list)
    certifications: list[str] = Field(default_factory=list)
    work_history: list[str] = Field(default_factory=list)
    projects: list[str] = Field(default_factory=list)
    technologies: list[str] = Field(default_factory=list)


class CandidateResult(BaseModel):
    """Full evaluation result for a single candidate."""
    id: str
    candidate_name: str
    email: str = ""
    overall_score: int = Field(ge=0, le=100)
    overall_recommendation: RecommendationType
    jd_match_score: int = Field(ge=0, le=100)
    skill_scores: list[SkillScore] = Field(default_factory=list)
    missing_skills: list[str] = Field(default_factory=list)
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)
    summary: str = ""
    recommendation: str = ""
    interview_questions: list[str] = Field(default_factory=list)
    resume_url: str = ""
    resume_filename: str = ""
    shortlisted: bool = False
    notes: list[str] = Field(default_factory=list)
    parsed_profile: Optional[ParsedProfile] = None

    class Config:
        json_schema_extra = {
            "example": {
                "id": "c1",
                "candidate_name": "John Doe",
                "email": "john.doe@email.com",
                "overall_score": 87,
                "overall_recommendation": "Strong Match",
                "jd_match_score": 84,
                "skill_scores": [
                    {
                        "skill": "Cloud Engineering",
                        "score": 91,
                        "confidence": "High",
                        "evidence": ["Built Azure Kubernetes infrastructure", "Implemented Terraform deployments"]
                    }
                ],
                "missing_skills": ["CrewAI", "Advanced Kubernetes"],
                "strengths": ["Strong cloud infrastructure experience"],
                "weaknesses": ["Limited agentic AI framework experience"],
                "summary": "Experienced engineer with strong cloud skills...",
                "recommendation": "Recommend for technical interview",
                "interview_questions": ["Describe your experience with Kubernetes orchestration"]
            }
        }


class EvaluationResponse(BaseModel):
    """Response containing all evaluated candidates."""
    evaluation_id: str
    status: EvaluationStatus
    job_title: str = ""
    job_description_preview: str = ""
    skills_evaluated: list[str] = Field(default_factory=list)
    total_resumes_processed: int = 0
    candidates: list[CandidateResult] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    processing_time_seconds: Optional[float] = None


class EvaluationStatusResponse(BaseModel):
    """Status check response for an ongoing evaluation."""
    evaluation_id: str
    status: EvaluationStatus
    progress_percent: int = Field(default=0, ge=0, le=100)
    message: str = ""
    total_resumes: int = 0
    processed_resumes: int = 0


class EvaluationHistoryItem(BaseModel):
    """Summary of a past evaluation."""
    evaluation_id: str
    job_title: str
    skills_evaluated: list[str]
    total_candidates: int
    top_candidate: str = ""
    top_score: int = 0
    created_at: datetime
    status: EvaluationStatus


class CandidateListResponse(BaseModel):
    """Paginated candidate list."""
    candidates: list[CandidateResult]
    total: int
    page: int
    page_size: int
    total_pages: int


class HealthResponse(BaseModel):
    """Health check response."""
    status: str = "healthy"
    version: str
    mock_mode: bool
    services: dict[str, str] = Field(default_factory=dict)
