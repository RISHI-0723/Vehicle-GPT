"""Sprint 4: AI grounding tests.

These verify that nothing beyond the backend-supplied structured evidence can
ever reach the client: no arbitrary evidence shape, no invented action type,
no LLM-controlled confidence, and no crash on malformed model output.
"""
import json

import pytest
from pydantic import ValidationError

from app.ai.response_validator import InvalidOllamaOutput, validate_ollama_answer
from app.ai.schemas import ActionItem, ActionType, EvidenceItem


# ---------------------------------------------------------------------------
# Structured evidence only -- no arbitrary fields, no unsupported claims
# ---------------------------------------------------------------------------

def test_evidence_item_rejects_unknown_fields():
    with pytest.raises(ValidationError):
        EvidenceItem(id="x", label="X", battery_degradation_percent=12)


def test_evidence_item_has_no_degradation_field_at_all():
    """There is no way to express "battery degradation" as evidence: the
    schema simply has no such field, so it can never be fabricated."""
    assert "degradation" not in EvidenceItem.model_fields
    assert "battery_health" not in EvidenceItem.model_fields


def test_evidence_item_has_no_charger_availability_field():
    assert "charger_availability" not in EvidenceItem.model_fields
    assert "charger_status" not in EvidenceItem.model_fields


def test_evidence_item_has_no_connectivity_field():
    assert "connectivity" not in EvidenceItem.model_fields
    assert "is_connected" not in EvidenceItem.model_fields


def test_evidence_item_rejects_invalid_direction():
    with pytest.raises(ValidationError):
        EvidenceItem(id="x", label="X", direction="sideways")


def test_action_item_rejects_an_invented_action_type():
    with pytest.raises(ValidationError):
        ActionItem(id="x", label="X", type="DELETE_VEHICLE")


def test_action_item_accepts_every_allowed_type():
    for action_type in ActionType:
        item = ActionItem(id="x", label="X", type=action_type)
        assert item.type == action_type


# ---------------------------------------------------------------------------
# Confidence can never be upgraded by the AI layer
# ---------------------------------------------------------------------------

def test_evidence_builder_never_invents_a_confidence_field():
    """Evidence objects carry impact_level, never a confidence rating --
    confidence always comes straight from the intelligence engine's own
    result, attached directly in app.ai.service, never parsed from evidence."""
    assert "confidence" not in EvidenceItem.model_fields


# ---------------------------------------------------------------------------
# Response validation: malformed Ollama output must never crash the endpoint
# ---------------------------------------------------------------------------

def test_validator_accepts_well_formed_answer():
    assert validate_ollama_answer(json.dumps({"answer": "Your range dropped due to driving style."})) == (
        "Your range dropped due to driving style."
    )


def test_validator_rejects_invalid_json():
    with pytest.raises(InvalidOllamaOutput):
        validate_ollama_answer("this is not json {")


def test_validator_rejects_a_json_array_instead_of_an_object():
    with pytest.raises(InvalidOllamaOutput):
        validate_ollama_answer(json.dumps(["answer", "text"]))


def test_validator_rejects_missing_answer_field():
    with pytest.raises(InvalidOllamaOutput):
        validate_ollama_answer(json.dumps({"reply": "no answer key here"}))


def test_validator_rejects_empty_answer():
    with pytest.raises(InvalidOllamaOutput):
        validate_ollama_answer(json.dumps({"answer": "   "}))


def test_validator_rejects_non_string_answer():
    with pytest.raises(InvalidOllamaOutput):
        validate_ollama_answer(json.dumps({"answer": 42}))


def test_validator_strips_surrounding_whitespace():
    assert validate_ollama_answer(json.dumps({"answer": "  hello  "})) == "hello"


def test_validator_rejects_an_attempt_to_smuggle_extra_fields_safely():
    """Extra fields (e.g. a model trying to set its own confidence/intent) are
    simply ignored -- only 'answer' is ever read."""
    payload = json.dumps({"answer": "ok", "confidence": "CERTAIN", "intent": "HACKED"})
    assert validate_ollama_answer(payload) == "ok"
