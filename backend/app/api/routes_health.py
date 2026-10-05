"""Health check endpoint."""
from fastapi import APIRouter
from pydantic import BaseModel

from app.core.config import settings


router = APIRouter()


class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    app_name: str
    version: str


@router.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    """Check API health status.

    Returns basic application health information.
    """
    return HealthResponse(
        status="healthy",
        app_name=settings.APP_NAME,
        version=settings.APP_VERSION,
    )
