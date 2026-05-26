"""
Evaluation endpoints — trigger and monitor candidate evaluations.
"""

from fastapi import APIRouter, BackgroundTasks, Request, HTTPException

from app.models.schemas import (
    EvaluationRequest,
    EvaluationResponse,
    EvaluationStatusResponse,
    EvaluationStatus,
)
from app.services.evaluation_service import get_evaluation_engine
from app.utils.logger import get_logger

router = APIRouter()
logger = get_logger("router.evaluate")


@router.post("/evaluate", response_model=EvaluationResponse)
async def evaluate_candidates(
    request: EvaluationRequest,
    background_tasks: BackgroundTasks,
    req: Request,
):
    """
    Evaluate candidates against a job description.
    Triggers the full pipeline: fetch → parse → embed → index → evaluate.
    """
    logger.info(f"Evaluation requested: {request.job_title or 'Untitled'} with {len(request.skills)} skills")

    engine = get_evaluation_engine()

    # For simplicity, run synchronously (can be moved to background task for large batches)
    result = await engine.evaluate(request)

    # Store in app state for later retrieval
    req.app.state.evaluations[result.evaluation_id] = result

    # Also store individual candidates
    for candidate in result.candidates:
        req.app.state.candidates[candidate.id] = candidate

    return result


@router.get("/evaluate/{evaluation_id}/status", response_model=EvaluationStatusResponse)
async def get_evaluation_status(evaluation_id: str, req: Request):
    """Check the status of an ongoing evaluation."""
    evaluations = req.app.state.evaluations

    if evaluation_id not in evaluations:
        raise HTTPException(status_code=404, detail="Evaluation not found")

    eval_data = evaluations[evaluation_id]
    return EvaluationStatusResponse(
        evaluation_id=evaluation_id,
        status=eval_data.status,
        progress_percent=100 if eval_data.status == EvaluationStatus.COMPLETED else 0,
        message="Evaluation complete" if eval_data.status == EvaluationStatus.COMPLETED else "Processing...",
        total_resumes=eval_data.total_resumes_processed,
        processed_resumes=eval_data.total_resumes_processed,
    )
