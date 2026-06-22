"""
FastAPI application entry point.
Configures middleware, routers, exception handlers, and lifespan events.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
import time
import os

from app.config import get_settings
from app.utils.logger import setup_logging, get_logger
from app.routers import evaluate, candidates, sharepoint, history, health, interview

logger = get_logger("main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    setup_logging(debug=settings.DEBUG, structured=not settings.DEBUG)
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")

    # ─── Fail-Fast Startup Validation ───
    required_configs = {
        "AZURE_OPENAI_ENDPOINT": settings.AZURE_OPENAI_ENDPOINT,
        "AZURE_OPENAI_API_KEY": settings.AZURE_OPENAI_API_KEY,
        "AZURE_SEARCH_ENDPOINT": settings.AZURE_SEARCH_ENDPOINT,
        "AZURE_SEARCH_API_KEY": settings.AZURE_SEARCH_API_KEY,
        "AZURE_DOC_INTELLIGENCE_ENDPOINT": settings.AZURE_DOC_INTELLIGENCE_ENDPOINT,
        "AZURE_DOC_INTELLIGENCE_KEY": settings.AZURE_DOC_INTELLIGENCE_KEY,
        "AZURE_STORAGE_CONNECTION_STRING": settings.AZURE_STORAGE_CONNECTION_STRING,
        "AZURE_COSMOS_ENDPOINT": settings.AZURE_COSMOS_ENDPOINT,
        "AZURE_COSMOS_KEY": settings.AZURE_COSMOS_KEY,
        "AZURE_SPEECH_KEY": settings.AZURE_SPEECH_KEY,
        "SMTP_USER": settings.SMTP_USER,
        "SMTP_PASSWORD": settings.SMTP_PASSWORD
    }

    missing = []
    for key, value in required_configs.items():
        if not value or "your-" in value.lower() or value == "...":
            missing.append(key)
    
    if missing:
        error_msg = f"Missing or placeholder required configurations: {', '.join(missing)}"
        logger.error(error_msg)
        raise RuntimeError(error_msg)


    from app.db.session_db import get_interview_db
    from app.db.evaluation_db import get_evaluation_db
    
    get_interview_db()
    get_evaluation_db()

    yield
    logger.info("Shutting down application")


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title=settings.APP_NAME,
        description="AI-powered resume scanning and candidate evaluation platform",
        version=settings.APP_VERSION,
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    origins = list(settings.cors_origin_list)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ─── Global exception handler ───
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        logger.error(f"Unhandled exception: {exc}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={
                "detail": "An internal error occurred. Please try again.",
                "error_type": type(exc).__name__,
            },
        )

    # ─── Rate Limiting ───
    from slowapi.errors import RateLimitExceeded
    from slowapi import _rate_limit_exceeded_handler
    from app.utils.security import limiter

    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    # ─── Routers ───
    app.include_router(health.router, tags=["Health"])
    app.include_router(evaluate.router, prefix="/api", tags=["Evaluation"])
    app.include_router(candidates.router, prefix="/api", tags=["Candidates"])
    app.include_router(sharepoint.router, prefix="/api", tags=["SharePoint"])
    app.include_router(history.router, prefix="/api", tags=["History"])
    app.include_router(interview.router, prefix="/interview", tags=["Interview"])

    # Serve local resumes
    os.makedirs("resumes", exist_ok=True)
    app.mount("/resumes", StaticFiles(directory="resumes"), name="resumes")

    return app


app = create_app()
