"""Orchestrates one /api/v1/ai/ask request end to end.

question -> deterministic intent -> deterministic intelligence -> structured
evidence/actions -> Ollama formatter (or deterministic fallback) -> validated
AskResponse.

This module NEVER lets Ollama supply confidence, intent, evidence, or
actions -- those always come from the intelligence engine or the fixed
per-intent action allow-list. Ollama only ever contributes the "answer" text.
"""
import logging
from typing import List, Optional

from sqlalchemy.orm import Session

from app.ai import evidence as ev
from app.ai import fallback as fb
from app.ai import intelligence_bridge as bridge
from app.ai.config import ai_settings
from app.ai.conversation import bound_conversation
from app.ai.intent_router import classify_intent
from app.ai.ollama_client import (
    OllamaError,
    chat,
    check_ollama_available,
)
from app.ai.response_validator import InvalidOllamaOutput, validate_ollama_answer
from app.ai.schemas import ActionItem, AskRequest, AskResponse, ConversationMessage, EvidenceItem, Intent
from app.ai.system_prompt import VEHICLEGPT_SYSTEM_PROMPT
from app.schemas.intelligence import ConfidenceLevel

logger = logging.getLogger(__name__)

NO_SIMULATION_MESSAGE = "No suitable driving simulation is available for this vehicle."
WHAT_IF_FAILURE_MESSAGE = "The counterfactual simulation could not be completed. Please try again."


class IntelligenceUnavailableError(Exception):
    """Raised when the requested vehicle intelligence cannot be produced.

    Distinct from any Ollama failure: this always means the backend must
    return a driver-friendly API error, never a fabricated AI answer.
    """

    def __init__(self, message: str, status_code: int = 404):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class WhatIfFailedError(Exception):
    """Raised when the counterfactual simulation itself could not complete."""


def _build_ollama_messages(
    conversation: List[ConversationMessage],
    question: str,
    intent: Intent,
    evidence: List[EvidenceItem],
    actions: List[ActionItem],
    confidence: ConfidenceLevel,
) -> List[dict]:
    """Bounded conversation -> Ollama /api/chat messages. The system prompt is
    always backend-owned and always first; the frontend can never supply one."""
    messages: List[dict] = [{"role": "system", "content": VEHICLEGPT_SYSTEM_PROMPT}]
    for turn in conversation:
        messages.append({"role": turn.role, "content": turn.content})

    evidence_text = "\n".join(
        f"- {e.label}: {e.value if e.value is not None else ''} {e.unit or ''} "
        f"{('(' + e.comparison + ')') if e.comparison else ''}".strip()
        for e in evidence
    ) or "No structured evidence is available for this question."
    actions_text = ", ".join(a.id for a in actions) or "none"

    context = (
        f"Detected intent: {intent.value}\n"
        f"Confidence from the intelligence engine: {confidence.value}\n"
        f"Structured evidence:\n{evidence_text}\n"
        f"Allowed action ids (for your own awareness only, the application attaches them): {actions_text}\n\n"
        f"Driver question: {question}"
    )
    messages.append({"role": "user", "content": context})
    return messages


async def _get_ollama_answer(messages: List[dict]) -> Optional[str]:
    """Returns a validated answer string, or None if Ollama is unavailable,
    timed out, or returned something that failed validation."""
    if ai_settings.AI_PROVIDER != "ollama":
        return None
    try:
        if not await check_ollama_available():
            return None
        raw = await chat(messages)
        return validate_ollama_answer(raw)
    except (OllamaError, InvalidOllamaOutput) as exc:
        logger.info("Falling back to deterministic answer: %s", exc)
        return None


async def answer_question(db: Session, request: AskRequest) -> AskResponse:
    """Answer one driver question. Raises IntelligenceUnavailableError or
    WhatIfFailedError for the caller (the route) to map to a driver-friendly
    HTTP error -- never returns a fabricated AI answer in those cases."""
    intent = classify_intent(request.question)
    conversation = bound_conversation(request.conversation)

    if intent == Intent.UNKNOWN:
        return AskResponse(
            intent=Intent.UNKNOWN,
            answer=fb.UNKNOWN_INTENT_COPY,
            evidence=[],
            actions=[],
            confidence=ConfidenceLevel.LOW,
            data_sources=[],
            provider="deterministic",
            fallback_used=True,
        )

    if intent == Intent.COST:
        if request.electricity_price_per_kwh is None:
            return AskResponse(
                intent=Intent.COST,
                answer=fb.COST_NEEDS_PRICE_COPY,
                evidence=[],
                actions=[ev.OPEN_COST_ACTION],
                confidence=ConfidenceLevel.HIGH,
                data_sources=[],
                provider="deterministic",
                fallback_used=False,
            )
        try:
            cost_result = bridge.calculate_cost(
                db, request.vehicle_id, None, request.electricity_price_per_kwh
            )
        except ValueError as exc:
            raise IntelligenceUnavailableError(NO_SIMULATION_MESSAGE, status_code=404) from exc

        evidence = ev.build_cost_evidence(cost_result)
        actions: List[ActionItem] = []
        confidence = ConfidenceLevel.HIGH
        messages = _build_ollama_messages(conversation, request.question, intent, evidence, actions, confidence)
        answer = await _get_ollama_answer(messages)
        fallback_used = answer is None
        if answer is None:
            answer = fb.fallback_cost_answer(cost_result)
        return AskResponse(
            intent=intent,
            answer=answer,
            evidence=evidence,
            actions=actions,
            confidence=confidence,
            data_sources=["cost"],
            provider="deterministic" if fallback_used else "ollama",
            fallback_used=fallback_used,
        )

    if intent == Intent.WHAT_IF:
        try:
            result = bridge.run_what_if(
                db,
                request.vehicle_id,
                scenario="NORMAL_DRIVING",
                base_simulation_id=None,
                seed=42,
                duration_minutes=30,
                interval_seconds=10,
            )
        except ValueError as exc:
            raise WhatIfFailedError(WHAT_IF_FAILURE_MESSAGE) from exc

        evidence = ev.build_what_if_evidence(result)
        actions = []
        confidence = ConfidenceLevel.HIGH
        messages = _build_ollama_messages(conversation, request.question, intent, evidence, actions, confidence)
        answer = await _get_ollama_answer(messages)
        fallback_used = answer is None
        if answer is None:
            answer = fb.fallback_what_if_answer(result)
        return AskResponse(
            intent=intent,
            answer=answer,
            evidence=evidence,
            actions=actions,
            confidence=confidence,
            data_sources=["what-if"],
            provider="deterministic" if fallback_used else "ollama",
            fallback_used=fallback_used,
        )

    if intent == Intent.GENERAL_VEHICLE:
        try:
            vehicle_summary = bridge.get_vehicle_summary(db, request.vehicle_id)
        except ValueError as exc:
            raise IntelligenceUnavailableError(NO_SIMULATION_MESSAGE, status_code=404) from exc

        evidence = ev.build_general_vehicle_evidence(vehicle_summary)
        actions = ev.actions_for_intent(intent)
        confidence = vehicle_summary.intelligence.confidence
        messages = _build_ollama_messages(conversation, request.question, intent, evidence, actions, confidence)
        answer = await _get_ollama_answer(messages)
        fallback_used = answer is None
        if answer is None:
            answer = fb.fallback_general_vehicle_answer(vehicle_summary)
        return AskResponse(
            intent=intent,
            answer=answer,
            evidence=evidence,
            actions=actions,
            confidence=confidence,
            data_sources=["vehicle", "summary"],
            provider="deterministic" if fallback_used else "ollama",
            fallback_used=fallback_used,
        )

    # RANGE_DROP, ENERGY_EFFICIENCY, BATTERY_STRESS, ANOMALY, RECOMMENDATIONS, DRIVE_COMPARISON
    try:
        summary = bridge.get_why_range_dropped(db, request.vehicle_id)
    except ValueError as exc:
        raise IntelligenceUnavailableError(NO_SIMULATION_MESSAGE, status_code=404) from exc

    evidence_builders = {
        Intent.RANGE_DROP: ev.build_range_drop_evidence,
        Intent.ENERGY_EFFICIENCY: ev.build_energy_efficiency_evidence,
        Intent.BATTERY_STRESS: ev.build_battery_stress_evidence,
        Intent.ANOMALY: ev.build_anomaly_evidence,
        Intent.RECOMMENDATIONS: ev.build_recommendations_evidence,
        Intent.DRIVE_COMPARISON: ev.build_drive_comparison_evidence,
    }
    evidence = evidence_builders[intent](summary)
    actions = ev.actions_for_intent(intent)
    # Confidence is always the intelligence engine's own value -- never upgraded.
    confidence = summary.confidence

    messages = _build_ollama_messages(conversation, request.question, intent, evidence, actions, confidence)
    answer = await _get_ollama_answer(messages)
    fallback_used = answer is None
    if answer is None:
        answer = fb.fallback_answer(intent, summary)

    return AskResponse(
        intent=intent,
        answer=answer,
        evidence=evidence,
        actions=actions,
        confidence=confidence,
        data_sources=["why-range-dropped"],
        provider="deterministic" if fallback_used else "ollama",
        fallback_used=fallback_used,
    )
