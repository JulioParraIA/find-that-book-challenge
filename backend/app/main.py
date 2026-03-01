"""
main.py
-------
FastAPI application entry point for the Find That Book API.

Running locally:  uvicorn app.main:app --reload --port 8000
Running in Docker: uvicorn app.main:app --host 0.0.0.0 --port 8000
"""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.api.routes import router as search_router


def create_app() -> FastAPI:
    """Application factory. Creates and configures the FastAPI instance."""
    settings = get_settings()

    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    logger = logging.getLogger(__name__)

    application = FastAPI(
        title="Find That Book API",
        description="Library discovery service powered by Claude AI and Open Library.",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    allowed_origins = [origin.strip() for origin in settings.allowed_origins.split(",") if origin.strip()]
    application.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )

    logger.info("CORS configured. Allowed origins: %s", allowed_origins)
    application.include_router(search_router)
    logger.info("Find That Book API initialized.")

    return application


app = create_app()
