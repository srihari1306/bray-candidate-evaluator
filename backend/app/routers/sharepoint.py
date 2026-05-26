"""
SharePoint reindex endpoint.
"""

from fastapi import APIRouter
from app.utils.logger import get_logger

router = APIRouter()
logger = get_logger("router.sharepoint")


@router.post("/reindex")
async def reindex_resumes():
    """Trigger re-fetch and reindex of SharePoint resumes."""
    logger.info("Reindex requested")
    # In production, this would trigger a background job
    return {
        "status": "accepted",
        "message": "Reindexing will occur on next evaluation with reindex=true",
    }
