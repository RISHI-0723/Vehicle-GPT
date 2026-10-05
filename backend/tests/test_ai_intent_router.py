"""Sprint 4: deterministic intent router tests.

classify_intent is pure and must not require a database, Ollama, or any
other side effect.
"""
from app.ai.intent_router import classify_intent
from app.ai.schemas import Intent


def test_range_drop_intent():
    assert classify_intent("Why did my range drop?") == Intent.RANGE_DROP


def test_energy_efficiency_intent():
    assert classify_intent("How efficient was my drive?") == Intent.ENERGY_EFFICIENCY


def test_battery_stress_intent():
    assert classify_intent("Is my battery stressed?") == Intent.BATTERY_STRESS


def test_anomaly_intent():
    assert classify_intent("Did anything unusual happen?") == Intent.ANOMALY


def test_cost_intent():
    assert classify_intent("How much did that drive cost?") == Intent.COST


def test_what_if_intent():
    assert classify_intent("What if I drove normally?") == Intent.WHAT_IF


def test_recommendations_intent():
    assert classify_intent("What should I change?") == Intent.RECOMMENDATIONS


def test_drive_comparison_intent():
    assert classify_intent("Was this worse than normal?") == Intent.DRIVE_COMPARISON


def test_general_vehicle_intent():
    assert classify_intent("What vehicle is this?") == Intent.GENERAL_VEHICLE


def test_unknown_intent():
    assert classify_intent("Tell me a joke") == Intent.UNKNOWN


def test_unknown_for_empty_input():
    assert classify_intent("") == Intent.UNKNOWN
    assert classify_intent("   ") == Intent.UNKNOWN


def test_what_if_wins_over_why_wording():
    """"what if" must outrank the bare word "why" per the locked rule order."""
    assert classify_intent("What if I understood why this happened?") == Intent.WHAT_IF


def test_classification_is_case_insensitive():
    assert classify_intent("WHY DID MY RANGE DROP") == Intent.RANGE_DROP


def test_inefficient_phrasing_still_matches_efficiency():
    assert classify_intent("Was this drive inefficient?") == Intent.ENERGY_EFFICIENCY


def test_spend_phrasing_matches_cost():
    assert classify_intent("How much did I spend on electricity?") == Intent.COST
