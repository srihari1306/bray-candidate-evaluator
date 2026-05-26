"""
Candidate management endpoints.
"""

from fastapi import APIRouter, Request, HTTPException, Query
from fastapi.responses import StreamingResponse
import io
import math

from app.models.schemas import (
    CandidateResult,
    CandidateListResponse,
    ShortlistRequest,
    NoteRequest,
)
from app.services.export_service import get_export_service
from app.utils.logger import get_logger

router = APIRouter()
logger = get_logger("router.candidates")


@router.get("/candidates", response_model=CandidateListResponse)
async def list_candidates(
    req: Request,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    sort_by: str = Query(default="overall_score"),
    sort_order: str = Query(default="desc"),
    search: str = Query(default=""),
    min_score: int = Query(default=0, ge=0, le=100),
    evaluation_id: str = Query(default=""),
):
    """Get paginated, sorted, filterable candidate list."""
    candidates: list[CandidateResult] = list(req.app.state.candidates.values())

    # Filter by evaluation if specified
    if evaluation_id and evaluation_id in req.app.state.evaluations:
        eval_data = req.app.state.evaluations[evaluation_id]
        candidates = eval_data.candidates

    # Filter by search term
    if search:
        search_lower = search.lower()
        candidates = [
            c for c in candidates
            if search_lower in c.candidate_name.lower()
            or search_lower in c.email.lower()
            or any(search_lower in s.skill.lower() for s in c.skill_scores)
        ]

    # Filter by minimum score
    if min_score > 0:
        candidates = [c for c in candidates if c.overall_score >= min_score]

    # Sort
    reverse = sort_order == "desc"
    if sort_by == "overall_score":
        candidates.sort(key=lambda c: c.overall_score, reverse=reverse)
    elif sort_by == "name":
        candidates.sort(key=lambda c: c.candidate_name.lower(), reverse=reverse)
    elif sort_by == "jd_match":
        candidates.sort(key=lambda c: c.jd_match_score, reverse=reverse)

    # Paginate
    total = len(candidates)
    total_pages = math.ceil(total / page_size) if total > 0 else 1
    start = (page - 1) * page_size
    end = start + page_size
    page_candidates = candidates[start:end]

    return CandidateListResponse(
        candidates=page_candidates,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get("/candidate/{candidate_id}", response_model=CandidateResult)
async def get_candidate(candidate_id: str, req: Request):
    """Get detailed candidate information."""
    candidates = req.app.state.candidates
    if candidate_id not in candidates:
        raise HTTPException(status_code=404, detail="Candidate not found")
    return candidates[candidate_id]


@router.post("/candidates/{candidate_id}/shortlist")
async def toggle_shortlist(candidate_id: str, body: ShortlistRequest, req: Request):
    """Toggle candidate shortlist status."""
    candidates = req.app.state.candidates
    if candidate_id not in candidates:
        raise HTTPException(status_code=404, detail="Candidate not found")
    candidates[candidate_id].shortlisted = body.shortlisted
    return {"status": "ok", "shortlisted": body.shortlisted}


@router.post("/candidates/{candidate_id}/notes")
async def add_note(candidate_id: str, body: NoteRequest, req: Request):
    """Add a recruiter note to a candidate."""
    candidates = req.app.state.candidates
    if candidate_id not in candidates:
        raise HTTPException(status_code=404, detail="Candidate not found")
    candidates[candidate_id].notes.append(body.content)
    return {"status": "ok", "total_notes": len(candidates[candidate_id].notes)}


@router.get("/export/{evaluation_id}")
async def export_candidates(
    evaluation_id: str,
    req: Request,
    format: str = Query(default="xlsx", pattern="^(csv|xlsx)$"),
):
    """Export evaluation results to CSV or Excel."""
    evaluations = req.app.state.evaluations
    if evaluation_id not in evaluations:
        raise HTTPException(status_code=404, detail="Evaluation not found")

    eval_data = evaluations[evaluation_id]
    export_service = get_export_service()
    skill_names = eval_data.skills_evaluated

    if format == "csv":
        data = export_service.export_to_csv(eval_data.candidates, skill_names)
        media_type = "text/csv"
        filename = f"candidates_{evaluation_id}.csv"
    else:
        data = export_service.export_to_excel(eval_data.candidates, skill_names)
        media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        filename = f"candidates_{evaluation_id}.xlsx"

    return StreamingResponse(
        io.BytesIO(data),
        media_type=media_type,
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
