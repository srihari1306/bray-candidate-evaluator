"""
Health check endpoint.
"""

from fastapi import APIRouter

from app.config import get_settings
from app.models.schemas import HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Check application health and service availability."""
    settings = get_settings()

    services = {
        "api": "healthy",
        "azure_openai": "configured" if settings.AZURE_OPENAI_ENDPOINT else "not configured",
        "azure_search": "configured" if settings.AZURE_SEARCH_ENDPOINT else "not configured",
        "azure_doc_intelligence": "configured" if settings.AZURE_DOC_INTELLIGENCE_ENDPOINT else "not configured",
        "sharepoint": "configured" if settings.SHAREPOINT_DRIVE_ID else "not configured",
    }

    return HealthResponse(
        status="healthy",
        version=settings.APP_VERSION,
        services=services,
    )
