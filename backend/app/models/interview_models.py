
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from enum import Enum


class InterviewStatus(str, Enum):
    SCHEDULED = "scheduled"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"



class ScheduleInterviewRequest(BaseModel):
    candidate_id: str = Field(..., description="Candidate ID from resume scanner")
    candidate_name: str = Field(..., description="Candidate full name")
    candidate_email: str = Field(..., description="Candidate email address")
    scheduled_time: str = Field(..., description="ISO 8601 datetime for interview")
    job_description_id: str = Field(default="", description="Links back to the JD evaluation")
    evaluation_id: str = Field(..., description="Evaluation ID that this session belongs to")


class AnswerInput(BaseModel):
    question_index: int = Field(..., ge=0, le=2)
    question_text: str
    transcript: str


class SubmitAnswersRequest(BaseModel):
    session_id: str
    exp: str = ""
    sig: str = ""
    answers: list[AnswerInput]
    recording_blob_name: str = Field(default="", description="Blob name of uploaded recording")
    camera_blob_name: str = Field(default="", description="Blob name of uploaded camera recording")
    focus_events: list[dict] = []


# ─── Response Models ────────────────────────────────────────────────────────

class ScheduleInterviewResponse(BaseModel):
    session_id: str
    status: InterviewStatus = InterviewStatus.SCHEDULED
    teams_link: str = ""
    message: str = "Interview scheduled successfully"


class SessionResponse(BaseModel):
    session_id: str
    candidate_name: str
    questions: list[str]
    status: InterviewStatus


class SpeechTokenResponse(BaseModel):
    token: str
    region: str


class UploadUrlResponse(BaseModel):
    sas_url: str
    blob_name: str


class ScoredAnswer(BaseModel):
    question_index: int
    question_text: str
    transcript: str
    score: int = Field(ge=0, le=10)
    score_reasoning: str = ""


class InterviewResultsResponse(BaseModel):
    session_id: str
    candidate_id: str
    candidate_name: str = ""
    status: InterviewStatus
    scheduled_time: str = ""
    final_score: Optional[float] = None
    answers: list[ScoredAnswer] = Field(default_factory=list)
    recording_sas_url: str = ""
    camera_sas_url: str = ""
    completed_at: Optional[str] = None
    proctoring_status: Optional[str] = None
    proctoring_report: Optional[dict] = None


class InterviewSessionDocument(BaseModel):
    id: str  # session UUID
    candidate_id: str
    candidate_name: str
    candidate_email: str
    job_description_id: str = ""
    status: InterviewStatus = InterviewStatus.SCHEDULED
    scheduled_time: str = ""
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    completed_at: Optional[str] = None
    questions: list[str] = Field(default_factory=list)
    answers: list[dict] = Field(default_factory=list)
    final_score: Optional[float] = None
    recording_blob_url: str = ""
    recording_sas_url: str = ""
    camera_blob_url: str = ""
    camera_sas_url: str = ""
