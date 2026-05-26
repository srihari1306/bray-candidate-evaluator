"""
Evaluation history endpoints.
"""

from fastapi import APIRouter, Request

from app.models.schemas import EvaluationHistoryItem, EvaluationStatus
from app.utils.logger import get_logger

router = APIRouter()
logger = get_logger("router.history")


@router.get("/history", response_model=list[EvaluationHistoryItem])
async def get_evaluation_history(req: Request):
    """Get list of past evaluations."""
    evaluations = req.app.state.evaluations
    history = []

    for eval_id, eval_data in evaluations.items():
        top_candidate = ""
        top_score = 0
        if eval_data.candidates:
            top = eval_data.candidates[0]
            top_candidate = top.candidate_name
            top_score = top.overall_score

        history.append(EvaluationHistoryItem(
            evaluation_id=eval_id,
            job_title=eval_data.job_title or "Untitled Evaluation",
            skills_evaluated=eval_data.skills_evaluated,
            total_candidates=len(eval_data.candidates),
            top_candidate=top_candidate,
            top_score=top_score,
            created_at=eval_data.created_at,
            status=eval_data.status,
        ))

    # Sort by most recent first
    history.sort(key=lambda h: h.created_at, reverse=True)
    return history
