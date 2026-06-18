"""
Orchestrator for Proctoring System (Phase 1 + Phase 2)
"""

import asyncio
from datetime import datetime

from app.models.proctoring_models import (
    BrowserSignals, TranscriptSignals, CameraSignals, ScreenSignals, ProctoringReport
)
from app.services.transcript_proctoring_service import analyze_transcript
from app.services.camera_analysis_service import analyze_camera_recording
from app.services.screen_analysis_service import analyze_screen_recording
from app.utils.logger import get_logger

logger = get_logger("services.proctoring")

def parse_browser_events(events: list) -> BrowserSignals:
    tab_switches = sum(1 for e in events if e.get('type') in ('blur', 'tab_hidden'))
    fullscreen_exits = sum(1 for e in events if e.get('type') == 'fullscreen_exit')
    
    return BrowserSignals(
        tab_switches=tab_switches,
        focus_lost_count=tab_switches,
        fullscreen_exits=fullscreen_exits,
        focus_lost_events=events
    )

def aggregate_signals(browser: BrowserSignals, transcript: TranscriptSignals, camera: CameraSignals, screen: ScreenSignals) -> ProctoringReport:
    risk_score = 0

    # Browser signals (max 50)
    # Tab switches (max 20)
    if browser.tab_switches >= 5:       risk_score += 20
    elif browser.tab_switches >= 3:     risk_score += 15
    elif browser.tab_switches >= 1:     risk_score += 8

    # Fullscreen exits (max 30) — stronger signal than tab switches
    if browser.fullscreen_exits >= 3:   risk_score += 30
    elif browser.fullscreen_exits >= 2: risk_score += 22
    elif browser.fullscreen_exits == 1: risk_score += 12

    # Camera (max 35)
    if camera.multiple_faces_detected and len(camera.multiple_faces_segments) >= 2:
        risk_score += 35
    elif camera.multiple_faces_detected and len(camera.multiple_faces_segments) == 1:
        risk_score += 10  # minor flag only, not definitive
    if camera.face_coverage_percent < 50:       risk_score += 20
    elif camera.face_coverage_percent < 75:     risk_score += 10

    # Screen (max 35)
    if screen.suspicious_urls_detected:         risk_score += 30
    if screen.suspicious_labels:                risk_score += 15
    if screen.suspicious_frame_count >= 5:      risk_score += 10

    # Transcript (max 20)
    if transcript.suspicion_score >= 8:         risk_score += 20
    elif transcript.suspicion_score >= 6:       risk_score += 12
    elif transcript.suspicion_score >= 4:       risk_score += 5

    risk_score = min(risk_score, 100)

    if risk_score >= 60:
        overall_risk = "high"
        cheating_detected = True
    elif risk_score >= 30:
        overall_risk = "medium"
        cheating_detected = False  # needs human review, not auto-flagged
    else:
        overall_risk = "low"
        cheating_detected = False

    return ProctoringReport(
        overall_risk=overall_risk,
        risk_score=risk_score,
        cheating_detected=cheating_detected,
        browser=browser,
        transcript=transcript,
        camera=camera,
        screen=screen,
        analyzed_at=datetime.utcnow().isoformat()
    )


async def _empty_camera() -> CameraSignals:
    return CameraSignals()


async def _empty_screen() -> ScreenSignals:
    return ScreenSignals()


async def analyze_session(session_id: str, focus_events: list, answers: list, session: dict) -> ProctoringReport:
    logger.info(f"Starting proctoring analysis for session {session_id}")

    # Step 1: Browser signals
    browser = parse_browser_events(focus_events)
    
    # Step 2: Transcript signals
    transcript = await analyze_transcript(answers)
    
    # Step 3: Camera + Screen analysis (Phase 2) — run in parallel
    camera_blob = session.get("camera_blob_url", "")
    screen_blob = session.get("recording_blob_url", "")

    camera_task = analyze_camera_recording(camera_blob) if camera_blob else _empty_camera()
    screen_task = analyze_screen_recording(screen_blob) if screen_blob else _empty_screen()

    camera, screen = await asyncio.gather(camera_task, screen_task)

    # Step 4: Compute risk score
    report = aggregate_signals(browser, transcript, camera, screen)
    
    logger.info(
        f"Proctoring analysis complete for {session_id}. "
        f"Score: {report.risk_score}, Risk: {report.overall_risk}, "
        f"Camera frames: {camera.frames_analyzed}, Screen frames: {screen.frames_analyzed}"
    )
    return report
