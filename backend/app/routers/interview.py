"""
Interview lifecycle routes for the Smart Interviewer.
Handles scheduling, session management, answer submission, evaluation, and results.
"""

import json
import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException
from app.config import get_settings
from app.models.interview_models import (
    ScheduleInterviewRequest,
    ScheduleInterviewResponse,
    SessionResponse,
    SubmitAnswersRequest,
    SpeechTokenResponse,
    UploadUrlResponse,
    InterviewResultsResponse,
    ScoredAnswer,
    InterviewStatus,
)
from app.db.session_db import get_interview_db
from app.services.email_service import send_interview_email
from app.services.speech_service import get_speech_token
from app.services.blob_recording_service import generate_upload_sas_url, generate_read_sas_url
from app.services.interview_evaluation_service import evaluate_answers
from app.utils.logger import get_logger

router = APIRouter()
logger = get_logger("router.interview")


@router.post("/schedule", response_model=ScheduleInterviewResponse)
async def schedule_interview(request: ScheduleInterviewRequest):
    """
    Schedule an interview for a candidate.
    Creates a session in the database and sends an email invitation.
    """
    settings = get_settings()
    db = get_interview_db()

    session_id = str(uuid.uuid4())
    questions = json.loads(settings.INTERVIEW_QUESTIONS)

    # Build the Teams link with session_id
    teams_link = settings.TEAMS_STATIC_MEETING_URL or "http://localhost:3001"

    # Create session document
    session_doc = {
        "id": session_id,
        "candidate_id": request.candidate_id,
        "evaluation_id": request.evaluation_id,
        "candidate_name": request.candidate_name,
        "candidate_email": request.candidate_email,
        "job_description_id": request.job_description_id,
        "status": InterviewStatus.SCHEDULED,
        "scheduled_time": request.scheduled_time,
        "created_at": datetime.utcnow().isoformat(),
        "completed_at": None,
        "questions": questions,
        "answers": [],
        "final_score": None,
        "recording_blob_url": "",
        "recording_sas_url": "",
    }

    try:
        await db.create_session(session_doc)
        logger.info(f"✓ Interview session created: {session_id} for {request.candidate_name}")
    except Exception as e:
        logger.error(f"✗ Failed to create session: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to create interview session: {str(e)}")

    # Send email to candidate
    try:
        await send_interview_email(
            candidate_name=request.candidate_name,
            candidate_email=request.candidate_email,
            scheduled_time=request.scheduled_time,
            teams_link=teams_link,
            session_id=session_id,
        )
    except Exception as e:
        logger.error(f"✗ Email send failed (session still created): {e}", exc_info=True)
        # Don't fail the whole request — session is created, email can be resent

    return ScheduleInterviewResponse(
        session_id=session_id,
        status=InterviewStatus.SCHEDULED,
        teams_link=teams_link,
        message=f"Interview scheduled for {request.candidate_name}",
    )


@router.get("/session/{session_id}", response_model=SessionResponse)
async def get_session(session_id: str):
    """
    Get session data and questions for the Teams panel.
    Updates session status to in_progress.
    """
    db = get_interview_db()

    session = await db.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Interview session not found")

    # Update status to in_progress
    if session.get("status") == InterviewStatus.SCHEDULED:
        try:
            await db.update_session(
                session_id,
                session["candidate_id"],
                {"status": InterviewStatus.IN_PROGRESS},
            )
            logger.info(f"Session {session_id} status → in_progress")
        except Exception as e:
            logger.warning(f"Failed to update session status: {e}")

    return SessionResponse(
        session_id=session_id,
        candidate_name=session.get("candidate_name", "Candidate"),
        questions=session.get("questions", []),
        status=InterviewStatus.IN_PROGRESS,
    )


@router.get("/speech-token", response_model=SpeechTokenResponse)
async def speech_token():
    """
    Get a short-lived Azure Speech auth token.
    Keeps the Speech key off the client.
    """
    try:
        result = await get_speech_token()
        return SpeechTokenResponse(token=result["token"], region=result["region"])
    except Exception as e:
        logger.error(f"Speech token request failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to obtain speech token")


@router.get("/upload-url/{session_id}", response_model=UploadUrlResponse)
async def get_upload_url(session_id: str):
    """
    Generate a SAS URL for uploading the interview recording.
    """
    try:
        result = generate_upload_sas_url(session_id)
        return UploadUrlResponse(sas_url=result["sas_url"], blob_name=result["blob_name"])
    except Exception as e:
        logger.error(f"Upload URL generation failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to generate upload URL")


@router.post("/answers", status_code=202)
async def submit_answers(request: SubmitAnswersRequest, background_tasks: BackgroundTasks):
    """
    Submit all interview answers. Triggers async evaluation.
    Returns 202 Accepted immediately so the panel doesn't wait.
    """
    db = get_interview_db()

    session = await db.get_session(request.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Interview session not found")

    # Save recording blob reference and SAS read URL
    if request.recording_blob_name:
        try:
            recording_sas_url = None
            try:
                recording_sas_url = generate_read_sas_url(request.recording_blob_name)
            except Exception as e:
                logger.warning(f"Failed to generate SAS read URL for {request.recording_blob_name}: {e}")

            await db.update_session(
                request.session_id,
                session["candidate_id"],
                {
                    "recording_blob_url": request.recording_blob_name,
                    "recording_sas_url": recording_sas_url,
                },
            )
        except Exception as e:
            logger.warning(f"Failed to save recording blob info: {e}")

    # Prepare answers for evaluation
    answers_data = [
        {
            "question_index": a.question_index,
            "question_text": a.question_text,
            "transcript": a.transcript,
        }
        for a in request.answers
    ]

    # Trigger async evaluation
    logger.info(f"Queuing evaluation for session {request.session_id} ({len(answers_data)} answers)")
    background_tasks.add_task(evaluate_answers, request.session_id, answers_data)

    return {"message": "Answers received. Evaluation in progress.", "session_id": request.session_id}


@router.get("/results/{session_id}", response_model=InterviewResultsResponse)
async def get_results(session_id: str):
    """
    Get interview results. Called by dashboard polling.
    """
    db = get_interview_db()

    session = await db.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Interview session not found")

    # Build scored answers from session data
    scored_answers = []
    for a in session.get("answers", []):
        scored_answers.append(ScoredAnswer(
            question_index=a.get("question_index", 0),
            question_text=a.get("question_text", ""),
            transcript=a.get("transcript", ""),
            score=a.get("score", 0),
            score_reasoning=a.get("score_reasoning", ""),
        ))

    # Generate recording SAS URL if available, fall back to what's stored in session document
    recording_sas_url = session.get("recording_sas_url") or ""
    recording_blob = session.get("recording_blob_url", "")
    if recording_blob:
        try:
            recording_sas_url = generate_read_sas_url(recording_blob)
        except Exception:
            pass

    return InterviewResultsResponse(
        session_id=session_id,
        candidate_id=session.get("candidate_id", ""),
        candidate_name=session.get("candidate_name", ""),
        status=InterviewStatus(session.get("status", "scheduled")),
        scheduled_time=session.get("scheduled_time", ""),
        final_score=session.get("final_score"),
        answers=scored_answers,
        recording_sas_url=recording_sas_url,
        completed_at=session.get("completed_at"),
    )


@router.get("/candidate/{candidate_id}")
async def get_candidate_session(candidate_id: str, evaluation_id: Optional[str] = None):
    """
    Get the latest interview session for a candidate.
    Called by dashboard on load to check existing session state.
    """
    db = get_interview_db()

    session = await db.get_candidate_sessions(candidate_id, evaluation_id)
    if not session:
        return {"session": None}

    # Build scored answers
    scored_answers = []
    for a in session.get("answers", []):
        scored_answers.append({
            "question_index": a.get("question_index", 0),
            "question_text": a.get("question_text", ""),
            "transcript": a.get("transcript", ""),
            "score": a.get("score", 0),
            "score_reasoning": a.get("score_reasoning", ""),
        })

    recording_sas_url = ""
    recording_blob = session.get("recording_blob_url", "")
    if recording_blob:
        try:
            recording_sas_url = generate_read_sas_url(recording_blob)
        except Exception:
            pass

    return {
        "session": {
            "session_id": session.get("id", ""),
            "candidate_id": session.get("candidate_id", ""),
            "candidate_name": session.get("candidate_name", ""),
            "status": session.get("status", "scheduled"),
            "scheduled_time": session.get("scheduled_time", ""),
            "final_score": session.get("final_score"),
            "answers": scored_answers,
            "recording_sas_url": recording_sas_url,
            "completed_at": session.get("completed_at"),
        }
    }
