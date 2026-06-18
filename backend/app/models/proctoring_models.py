from pydantic import BaseModel
from typing import Optional

class BrowserSignals(BaseModel):
    tab_switches: int = 0
    focus_lost_count: int = 0
    fullscreen_exits: int = 0
    focus_lost_events: list[dict] = []

class TranscriptSignals(BaseModel):
    suspicion_score: int = 0
    reasoning: str = ""

class CameraSignals(BaseModel):
    face_coverage_percent: float = 0.0
    multiple_faces_detected: bool = False
    multiple_faces_segments: list[dict] = []
    face_absent_segments: list[dict] = []
    frames_analyzed: int = 0

class ScreenSignals(BaseModel):
    suspicious_urls_detected: list[str] = []
    suspicious_labels: list[str] = []
    suspicious_frame_count: int = 0
    frames_analyzed: int = 0

class ProctoringReport(BaseModel):
    overall_risk: str = "low"
    risk_score: int = 0
    cheating_detected: bool = False
    browser: BrowserSignals = BrowserSignals()
    transcript: TranscriptSignals = TranscriptSignals()
    camera: CameraSignals = CameraSignals()
    screen: ScreenSignals = ScreenSignals()
    analyzed_at: Optional[str] = None

class ProctoringResponse(BaseModel):
    session_id: str
    proctoring_status: str
    report: Optional[ProctoringReport] = None

class ProctoringOverrideRequest(BaseModel):
    override_status: str  # "clean" | "flagged"
    note: str = ""
