"""Deterministic answer text, used whenever Ollama is unavailable, times out,
or returns something that fails validation. The product must stay useful
without any AI provider -- these templates reuse the same human-readable
fields Sprint 2 already computes (e.g. ExplanationBuilder's summary), never
new prose logic duplicating the intelligence engine.
"""
from app.ai.intelligence_bridge import VehicleSummary
from app.ai.schemas import Intent
from app.intelligence.cost import CostAnalysisResult
from app.intelligence.orchestrator import IntelligenceSummary
from app.intelligence.what_if import WhatIfResult

UNKNOWN_INTENT_COPY = (
    "I can help with range, efficiency, battery stress, drive comparisons, cost, "
    "and what-if scenarios."
)

COST_NEEDS_PRICE_COPY = "To calculate the drive cost, enter your electricity price."


def fallback_answer(intent: Intent, summary: IntelligenceSummary) -> str:
    """Deterministic fallback answer for intents grounded in the composite summary."""
    if intent == Intent.RANGE_DROP or intent == Intent.DRIVE_COMPARISON:
        return summary.explanation.summary
    if intent == Intent.ENERGY_EFFICIENCY:
        return summary.energy.rating_reason
    if intent == Intent.BATTERY_STRESS:
        return summary.battery_stress.explanation
    if intent == Intent.ANOMALY:
        if summary.anomaly.reasons:
            return " ".join(summary.anomaly.reasons)
        return "Your recent drive looks normal, with no unusual energy use detected."
    if intent == Intent.RECOMMENDATIONS:
        recs = summary.recommendations.recommendations
        if not recs:
            return "No specific recommendations for this drive."
        top = recs[0]
        return f"{top.title}: {top.reason} {top.expected_benefit}"
    return summary.explanation.summary


def fallback_general_vehicle_answer(vehicle_summary: VehicleSummary) -> str:
    v = vehicle_summary.vehicle
    return (
        f"This is a {v.make} {v.model} ({v.model_year}), {v.battery_type} battery, "
        f"{v.usable_battery_capacity_kwh:.0f} kWh usable. All data shown is from "
        f"synthetic simulated telemetry, not a physically connected vehicle."
    )


def fallback_cost_answer(result: CostAnalysisResult) -> str:
    return (
        f"This drive cost an estimated {result.total_operating_cost_inr:.2f} INR "
        f"({result.energy_cost_inr:.2f} INR energy"
        + (f", {result.cost_per_km_inr:.2f} INR/km" if result.cost_per_km_inr is not None else "")
        + ")."
    )


def fallback_what_if_answer(result: WhatIfResult) -> str:
    return result.interpretation
