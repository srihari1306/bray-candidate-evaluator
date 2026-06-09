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
    """Application lifespan: startup and shutdown events."""
    settings = get_settings()
    setup_logging(debug=settings.DEBUG, structured=not settings.DEBUG)
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")

    # Preload JSON databases into memory on startup
    from app.db.session_db import get_interview_db
    from app.db.evaluation_db import get_evaluation_db
    
    get_interview_db()
    get_evaluation_db()

    yield

    logger.info("Shutting down application")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title=settings.APP_NAME,
        description="AI-powered resume scanning and candidate evaluation platform",
        version=settings.APP_VERSION,
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # ─── CORS ───
    origins = list(settings.cors_origin_list)
    for port_origin in ["http://localhost:3001", "http://127.0.0.1:3001"]:
        if port_origin not in origins:
            origins.append(port_origin)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ─── Request timing middleware ───
    @app.middleware("http")
    async def add_timing_header(request: Request, call_next):
        start = time.perf_counter()
        response = await call_next(request)
        elapsed = time.perf_counter() - start
        response.headers["X-Process-Time"] = f"{elapsed:.3f}s"
        return response

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
