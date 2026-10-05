"""Pydantic schemas for the Sprint 4 AI ask endpoint.

These are intentionally separate from app/schemas/intelligence.py: the AI
layer's request/response contract is its own thing, even though it is built
entirely from Sprint 2 intelligence data.
"""
from enum import Enum
from typing import List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.intelligence import ConfidenceLevel


class Intent(str, Enum):
    """Deterministic question intents the router can classify."""

    RANGE_DROP = "RANGE_DROP"
    ENERGY_EFFICIENCY = "ENERGY_EFFICIENCY"
    BATTERY_STRESS = "BATTERY_STRESS"
    ANOMALY = "ANOMALY"
    COST = "COST"
    WHAT_IF = "WHAT_IF"
    RECOMMENDATIONS = "RECOMMENDATIONS"
    DRIVE_COMPARISON = "DRIVE_COMPARISON"
    GENERAL_VEHICLE = "GENERAL_VEHICLE"
    UNKNOWN = "UNKNOWN"


class ActionType(str, Enum):
    """Allowed action types. The LLM may never invent a new one."""

    WHAT_IF = "WHAT_IF"
    VIEW_DRIVE = "VIEW_DRIVE"
    VIEW_CONTRIBUTORS = "VIEW_CONTRIBUTORS"
    VIEW_RECOMMENDATIONS = "VIEW_RECOMMENDATIONS"
    VIEW_COST = "VIEW_COST"
    VIEW_BATTERY = "VIEW_BATTERY"


class ConversationMessage(BaseModel):
    """One turn of bounded conversation history.

    Only user/assistant roles are accepted. The backend owns the system
    prompt, so a frontend-supplied "system" role is rejected outright.
    """

    model_config = ConfigDict(extra="forbid")

    role: Literal["user", "assistant"]
    content: str = Field(..., min_length=1, max_length=2000)


class EvidenceItem(BaseModel):
    """One structured piece of evidence grounding an answer.

    Only these fields are allowed -- no arbitrary evidence objects.
    """

    model_config = ConfigDict(extra="forbid")

    id: str
    label: str
    value: Optional[float] = None
    unit: Optional[str] = None
    comparison: Optional[str] = None
    direction: Optional[Literal["higher", "lower", "same"]] = None
    impact_level: Optional[str] = None


class ActionItem(BaseModel):
    """One suggested next action the UI can offer."""

    model_config = ConfigDict(extra="forbid")

    id: str
    label: str
    type: ActionType


class AskRequest(BaseModel):
    """Request body for POST /api/v1/ai/ask."""

    vehicle_id: str = Field(..., min_length=1)
    question: str = Field(..., min_length=1, max_length=500)
    conversation: List[ConversationMessage] = Field(default_factory=list)
    # Only present when the frontend already has a price in context (e.g. the
    # Cost screen). There is no hidden/default electricity price -- see
    # app/ai/service.py's handling of the COST intent.
    electricity_price_per_kwh: Optional[float] = Field(None, gt=0)


class AskResponse(BaseModel):
    """Response body for POST /api/v1/ai/ask."""

    intent: Intent
    answer: str
    evidence: List[EvidenceItem]
    actions: List[ActionItem]
    confidence: ConfidenceLevel
    data_sources: List[str]
    provider: Literal["ollama", "deterministic"]
    fallback_used: bool
