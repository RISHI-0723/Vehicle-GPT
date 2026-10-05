"""Sprint 4 AI ask endpoint.

This route is a thin HTTP adapter over app.ai.service -- all orchestration
(intent routing, intelligence lookup, Ollama call, fallback) lives there so
it stays independently testable without a TestClient.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.ai.schemas import AskRequest, AskResponse
from app.ai.service import IntelligenceUnavailableError, WhatIfFailedError, answer_question
from app.db.database import get_db

router = APIRouter(prefix="/api/v1/ai", tags=["ai"])


@router.post(
    "/ask",
    response_model=AskResponse,
    summary="Ask VehicleGPT",
    description=(
        "Answers a driver's question using deterministic intent routing and Sprint 2 "
        "vehicle intelligence, explained by a local Ollama model when available and a "
        "deterministic formatter otherwise. Never fabricates vehicle data."
    ),
)
async def ask(request: AskRequest, db: Session = Depends(get_db)) -> AskResponse:
    """Answer one driver question about the vehicle."""
    try:
        return await answer_question(db, request)
    except IntelligenceUnavailableError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
    except WhatIfFailedError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
