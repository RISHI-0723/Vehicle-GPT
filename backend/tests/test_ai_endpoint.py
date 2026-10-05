"""Sprint 4: end-to-end POST /api/v1/ai/ask tests.

Ollama is always mocked here (see conftest.py's mock_ollama_* fixtures) --
these tests never depend on a live model, per the Sprint 4 testing policy.
"""
import json

import pytest


# ---------------------------------------------------------------------------
# Tool / intent routing: each supported intent reaches the right intelligence
# ---------------------------------------------------------------------------

def test_range_drop_routes_to_why_range_dropped(client, demo_vehicle_id, run_aggressive_driving, mock_ollama_unavailable):
    response = client.post("/api/v1/ai/ask", json={
        "vehicle_id": demo_vehicle_id,
        "question": "Why did my range drop?",
    })
    assert response.status_code == 200
    body = response.json()
    assert body["intent"] == "RANGE_DROP"
    assert body["data_sources"] == ["why-range-dropped"]
    assert body["provider"] == "deterministic"
    assert body["fallback_used"] is True
    assert len(body["evidence"]) > 0


def test_energy_efficiency_routes_to_energy_analysis(client, demo_vehicle_id, run_aggressive_driving, mock_ollama_unavailable):
    response = client.post("/api/v1/ai/ask", json={
        "vehicle_id": demo_vehicle_id,
        "question": "How efficient was my drive?",
    })
    assert response.status_code == 200
    assert response.json()["intent"] == "ENERGY_EFFICIENCY"


def test_battery_stress_routes_to_battery_stress(client, demo_vehicle_id, run_aggressive_driving, mock_ollama_unavailable):
    response = client.post("/api/v1/ai/ask", json={
        "vehicle_id": demo_vehicle_id,
        "question": "Is my battery stressed?",
    })
    assert response.status_code == 200
    body = response.json()
    assert body["intent"] == "BATTERY_STRESS"
    assert any(e["id"] == "battery_stress_score" for e in body["evidence"])


def test_anomaly_routes_to_anomaly_analysis(client, demo_vehicle_id, run_aggressive_driving, mock_ollama_unavailable):
    response = client.post("/api/v1/ai/ask", json={
        "vehicle_id": demo_vehicle_id,
        "question": "Did anything unusual happen?",
    })
    assert response.status_code == 200
    assert response.json()["intent"] == "ANOMALY"


def test_recommendations_routes_to_recommendations(client, demo_vehicle_id, run_aggressive_driving, mock_ollama_unavailable):
    response = client.post("/api/v1/ai/ask", json={
        "vehicle_id": demo_vehicle_id,
        "question": "What should I change?",
    })
    assert response.status_code == 200
    assert response.json()["intent"] == "RECOMMENDATIONS"


def test_drive_comparison_routes_to_comparison_intelligence(client, demo_vehicle_id, run_aggressive_driving, mock_ollama_unavailable):
    response = client.post("/api/v1/ai/ask", json={
        "vehicle_id": demo_vehicle_id,
        "question": "Was this worse than normal?",
    })
    assert response.status_code == 200
    assert response.json()["intent"] == "DRIVE_COMPARISON"


def test_general_vehicle_routes_to_vehicle_summary(client, demo_vehicle_id, run_aggressive_driving, mock_ollama_unavailable):
    response = client.post("/api/v1/ai/ask", json={
        "vehicle_id": demo_vehicle_id,
        "question": "What vehicle is this?",
    })
    assert response.status_code == 200
    body = response.json()
    assert body["intent"] == "GENERAL_VEHICLE"
    assert any("VehicleGPT" in (e.get("comparison") or "") for e in body["evidence"])


def test_unknown_question_returns_capability_copy_with_no_evidence(client, demo_vehicle_id, mock_ollama_unavailable):
    response = client.post("/api/v1/ai/ask", json={
        "vehicle_id": demo_vehicle_id,
        "question": "Tell me a joke",
    })
    assert response.status_code == 200
    body = response.json()
    assert body["intent"] == "UNKNOWN"
    assert body["evidence"] == []
    assert body["actions"] == []
    assert "range" in body["answer"].lower()


# ---------------------------------------------------------------------------
# Tool / intelligence failure handling: driver-friendly errors, never fabricated
# ---------------------------------------------------------------------------

def test_no_simulation_returns_driver_friendly_404(client, demo_vehicle_id, mock_ollama_unavailable):
    """No simulation has been run at all for this vehicle."""
    response = client.post("/api/v1/ai/ask", json={
        "vehicle_id": demo_vehicle_id,
        "question": "Why did my range drop?",
    })
    assert response.status_code == 404
    detail = response.json()["detail"]
    assert "No suitable driving simulation" in detail
    assert "Traceback" not in detail


def test_unknown_vehicle_returns_404_not_a_crash(client, mock_ollama_unavailable):
    response = client.post("/api/v1/ai/ask", json={
        "vehicle_id": "NOT-A-REAL-VEHICLE",
        "question": "Why did my range drop?",
    })
    assert response.status_code == 404


def test_malformed_ollama_output_falls_back_without_crashing(
    client, demo_vehicle_id, run_aggressive_driving, mock_ollama_malformed
):
    mock_ollama_malformed("not valid json at all")
    response = client.post("/api/v1/ai/ask", json={
        "vehicle_id": demo_vehicle_id,
        "question": "Why did my range drop?",
    })
    assert response.status_code == 200
    body = response.json()
    assert body["provider"] == "deterministic"
    assert body["fallback_used"] is True
    assert len(body["answer"]) > 0


# ---------------------------------------------------------------------------
# Cost flow: no hidden electricity price
# ---------------------------------------------------------------------------

def test_cost_with_price_calculates_actual_cost(client, demo_vehicle_id, run_aggressive_driving, mock_ollama_unavailable):
    response = client.post("/api/v1/ai/ask", json={
        "vehicle_id": demo_vehicle_id,
        "question": "How much did that drive cost?",
        "electricity_price_per_kwh": 8.0,
    })
    assert response.status_code == 200
    body = response.json()
    assert body["intent"] == "COST"
    assert any(e["id"] == "total_operating_cost" for e in body["evidence"])
    assert body["actions"] == []


def test_cost_without_price_never_calculates_and_offers_the_cost_screen(
    client, demo_vehicle_id, run_aggressive_driving, mock_ollama_unavailable, monkeypatch
):
    import app.ai.service as ai_service

    def _must_not_be_called(*args, **kwargs):
        raise AssertionError("calculate_cost must never be called without a price")

    monkeypatch.setattr(ai_service.bridge, "calculate_cost", _must_not_be_called)

    response = client.post("/api/v1/ai/ask", json={
        "vehicle_id": demo_vehicle_id,
        "question": "How much did that drive cost?",
    })
    assert response.status_code == 200
    body = response.json()
    assert body["intent"] == "COST"
    assert body["evidence"] == []
    assert body["actions"] == [{"id": "OPEN_COST", "label": "Calculate drive cost", "type": "VIEW_COST"}]
    assert "price" in body["answer"].lower()


def test_cost_rejects_a_non_positive_price_at_the_request_boundary(client, demo_vehicle_id):
    response = client.post("/api/v1/ai/ask", json={
        "vehicle_id": demo_vehicle_id,
        "question": "How much did that drive cost?",
        "electricity_price_per_kwh": 0,
    })
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# What-if flow: no hardcoded UUID, canonical parameters, no mutation
# ---------------------------------------------------------------------------

def test_what_if_resolves_the_latest_aggressive_driving_simulation(
    client, demo_vehicle_id, run_aggressive_driving, mock_ollama_unavailable
):
    hero_simulation_id = run_aggressive_driving["simulation_id"]

    response = client.post("/api/v1/ai/ask", json={
        "vehicle_id": demo_vehicle_id,
        "question": "What if I drove normally?",
    })
    assert response.status_code == 200
    body = response.json()
    assert body["intent"] == "WHAT_IF"
    base_evidence = next(e for e in body["evidence"] if e["id"] == "base_range")
    assert hero_simulation_id  # the engine resolved a real, non-empty ID
    assert "AGGRESSIVE_DRIVING" in base_evidence["label"]


def test_what_if_never_receives_a_hardcoded_simulation_id(
    client, demo_vehicle_id, run_aggressive_driving, mock_ollama_unavailable, monkeypatch
):
    import app.ai.service as ai_service

    captured = {}
    original = ai_service.bridge.run_what_if

    def _spy(db, vehicle_id, **kwargs):
        captured.update(kwargs)
        return original(db, vehicle_id, **kwargs)

    monkeypatch.setattr(ai_service.bridge, "run_what_if", _spy)

    response = client.post("/api/v1/ai/ask", json={
        "vehicle_id": demo_vehicle_id,
        "question": "What if I drove normally?",
    })
    assert response.status_code == 200
    assert captured["base_simulation_id"] is None  # resolved server-side, never a literal UUID
    assert captured["scenario"] == "NORMAL_DRIVING"
    assert captured["seed"] == 42
    assert captured["duration_minutes"] == 30
    assert captured["interval_seconds"] == 10


def test_what_if_does_not_mutate_persisted_simulations(
    client, demo_vehicle_id, run_aggressive_driving, mock_ollama_unavailable
):
    before = client.get(f"/api/v1/vehicles/{demo_vehicle_id}/telemetry", params={"limit": 1000}).json()["count"]

    response = client.post("/api/v1/ai/ask", json={
        "vehicle_id": demo_vehicle_id,
        "question": "What if I drove normally?",
    })
    assert response.status_code == 200

    after = client.get(f"/api/v1/vehicles/{demo_vehicle_id}/telemetry", params={"limit": 1000}).json()["count"]
    assert after == before


def test_what_if_contextual_follow_up_needs_no_id_from_the_user(
    client, demo_vehicle_id, run_aggressive_driving, mock_ollama_unavailable
):
    """"What if I drove normally?" after "Why did my range drop?" resolves the
    base simulation itself; the frontend never has to supply one."""
    first = client.post("/api/v1/ai/ask", json={
        "vehicle_id": demo_vehicle_id,
        "question": "Why did my range drop?",
    })
    assert first.status_code == 200

    second = client.post("/api/v1/ai/ask", json={
        "vehicle_id": demo_vehicle_id,
        "question": "What if I drove normally?",
        "conversation": [
            {"role": "user", "content": "Why did my range drop?"},
            {"role": "assistant", "content": first.json()["answer"]},
        ],
    })
    assert second.status_code == 200
    assert second.json()["intent"] == "WHAT_IF"


# ---------------------------------------------------------------------------
# Misc response-shape guarantees
# ---------------------------------------------------------------------------

def test_response_never_includes_raw_telemetry_arrays(client, demo_vehicle_id, run_aggressive_driving, mock_ollama_unavailable):
    response = client.post("/api/v1/ai/ask", json={
        "vehicle_id": demo_vehicle_id,
        "question": "Why did my range drop?",
    })
    raw = response.text
    assert "telemetry_id" not in raw
    assert "soc_percent" not in raw


def test_evidence_payload_stays_well_under_the_six_kilobyte_context_budget(
    client, demo_vehicle_id, run_aggressive_driving, mock_ollama_unavailable
):
    response = client.post("/api/v1/ai/ask", json={
        "vehicle_id": demo_vehicle_id,
        "question": "Why did my range drop?",
    })
    evidence_bytes = len(json.dumps(response.json()["evidence"]).encode("utf-8"))
    assert evidence_bytes < 6 * 1024


def test_ollama_available_path_uses_the_models_answer_text(
    client, demo_vehicle_id, run_aggressive_driving, mock_ollama_answer
):
    captured_messages = mock_ollama_answer("Your range dropped because of aggressive driving.")

    response = client.post("/api/v1/ai/ask", json={
        "vehicle_id": demo_vehicle_id,
        "question": "Why did my range drop?",
    })
    assert response.status_code == 200
    body = response.json()
    assert body["provider"] == "ollama"
    assert body["fallback_used"] is False
    assert body["answer"] == "Your range dropped because of aggressive driving."
    # The backend-owned system prompt must always be first.
    assert captured_messages[0][0]["role"] == "system"


def test_confidence_is_never_upgraded_by_a_mocked_ollama_reply(
    client, demo_vehicle_id, run_aggressive_driving, mock_ollama_answer
):
    """Even if the model's text sounds confident, the response's confidence
    field must exactly match the intelligence engine's own value for the same
    drive -- never something the model's text implies."""
    mock_ollama_answer("I am absolutely certain your range dropped due to driving style.")

    ai_response = client.post("/api/v1/ai/ask", json={
        "vehicle_id": demo_vehicle_id,
        "question": "Why did my range drop?",
    })
    engine_response = client.get(f"/api/v1/intelligence/why-range-dropped/{demo_vehicle_id}")

    assert ai_response.json()["confidence"] == engine_response.json()["confidence"]
