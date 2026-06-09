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

    # Store in JSON database
    from fastapi.encoders import jsonable_encoder
    from app.db.evaluation_db import get_evaluation_db
    db = get_evaluation_db()
    await db.save_evaluation(result.evaluation_id, jsonable_encoder(result))

    return result


@router.get("/evaluate/{evaluation_id}/status", response_model=EvaluationStatusResponse)
async def get_evaluation_status(evaluation_id: str, req: Request):
    """Check the status of an ongoing evaluation."""
    from app.db.evaluation_db import get_evaluation_db
    db = get_evaluation_db()
    eval_data = db.get_evaluation(evaluation_id)

    if not eval_data:
        raise HTTPException(status_code=404, detail="Evaluation not found")

    status = eval_data.get("status")
    total_resumes = eval_data.get("total_resumes_processed", 0)

    return EvaluationStatusResponse(
        evaluation_id=evaluation_id,
        status=status,
        progress_percent=100 if status == EvaluationStatus.COMPLETED else 0,
        message="Evaluation complete" if status == EvaluationStatus.COMPLETED else "Processing...",
        total_resumes=total_resumes,
        processed_resumes=total_resumes,
    )
