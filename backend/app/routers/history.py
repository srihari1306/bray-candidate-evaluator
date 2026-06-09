"""
Evaluation history endpoints.
"""

from fastapi import APIRouter, Request

from app.models.schemas import EvaluationResponse, EvaluationStatus
from app.utils.logger import get_logger

router = APIRouter()
logger = get_logger("router.history")


@router.get("/history", response_model=list[EvaluationResponse])
async def get_evaluation_history(req: Request):
    """Get list of past evaluations."""
    from app.db.evaluation_db import get_evaluation_db
    db = get_evaluation_db()
    evaluations = db.get_all_evaluations()

    # Sort evaluations by creation date (descending), handling aware/naive string parses safely
    from datetime import datetime
    def get_created_at(eval_doc):
        created_at = eval_doc.get("created_at")
        if not created_at:
            return datetime.min
        if isinstance(created_at, datetime):
            dt = created_at
        else:
            try:
                dt_str = created_at.replace("Z", "")
                dt = datetime.fromisoformat(dt_str)
            except Exception:
                dt = datetime.min
        return dt.replace(tzinfo=None)

    evaluations.sort(key=get_created_at, reverse=True)
    return evaluations


@router.delete("/history/{evaluation_id}")
async def delete_evaluation(evaluation_id: str):
    """Delete an evaluation history item by ID."""
    from app.db.evaluation_db import get_evaluation_db
    db = get_evaluation_db()
    success = await db.delete_evaluation(evaluation_id)
    if not success:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Evaluation not found")
    return {"message": "Evaluation deleted successfully", "evaluation_id": evaluation_id}

