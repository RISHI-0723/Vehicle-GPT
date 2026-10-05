"""Builds structured Evidence/Action objects from Sprint 2 intelligence results.

Evidence is the ONLY grounding the LLM (or the deterministic fallback) may
reference -- every value here is read directly off an already-computed
Sprint 2 result object, never invented. Actions are a fixed, per-intent
allow-list; nothing here lets the LLM introduce a new action type.
"""
from typing import List, Optional

from app.ai.schemas import ActionItem, ActionType, EvidenceItem, Intent
from app.intelligence.cost import CostAnalysisResult
from app.intelligence.orchestrator import IntelligenceSummary
from app.intelligence.what_if import WhatIfResult
from app.ai.intelligence_bridge import VehicleSummary


def _direction(value: Optional[float], baseline: Optional[float]) -> Optional[str]:
    if value is None or baseline is None:
        return None
    if value > baseline:
        return "higher"
    if value < baseline:
        return "lower"
    return "same"


def _top_contributors(summary: IntelligenceSummary, limit: int = 3) -> List[EvidenceItem]:
    ranked = sorted(summary.contributors.contributors, key=lambda c: c.impact_score, reverse=True)
    return [
        EvidenceItem(
            id=f"contributor_{c.id}",
            label=c.name,
            value=c.observed_value,
            comparison=f"{c.baseline_value} baseline" if c.baseline_value is not None else None,
            direction=_direction(c.observed_value, c.baseline_value),
            impact_level=c.impact_level.value if c.is_available else "UNAVAILABLE",
        )
        for c in ranked[:limit]
    ]


def build_range_drop_evidence(summary: IntelligenceSummary) -> List[EvidenceItem]:
    energy = summary.energy
    items = [
        EvidenceItem(
            id="estimated_range",
            label="Estimated range",
            value=summary.range_estimate.estimated_range_km,
            unit="km",
        ),
        EvidenceItem(
            id="energy_consumption",
            label="Energy consumption",
            value=energy.efficiency_kwh_per_100km,
            unit="kWh/100km",
            comparison=(
                f"{energy.baseline_efficiency_kwh_per_100km:.1f} kWh/100km baseline"
                if energy.baseline_efficiency_kwh_per_100km is not None
                else None
            ),
            direction=_direction(energy.efficiency_kwh_per_100km, energy.baseline_efficiency_kwh_per_100km),
            impact_level=energy.rating.value,
        ),
    ]
    items.extend(_top_contributors(summary))
    return items


def build_energy_efficiency_evidence(summary: IntelligenceSummary) -> List[EvidenceItem]:
    energy = summary.energy
    return [
        EvidenceItem(
            id="energy_consumed",
            label="Energy consumed",
            value=energy.energy_consumed_kwh,
            unit="kWh",
        ),
        EvidenceItem(
            id="energy_regenerated",
            label="Energy regenerated",
            value=energy.energy_regenerated_kwh,
            unit="kWh",
        ),
        EvidenceItem(
            id="efficiency_rating",
            label="Efficiency rating",
            comparison=energy.rating_reason,
            impact_level=energy.rating.value,
        ),
    ]


def build_battery_stress_evidence(summary: IntelligenceSummary) -> List[EvidenceItem]:
    stress = summary.battery_stress
    return [
        EvidenceItem(
            id="battery_stress_score",
            label="Battery operating stress",
            value=stress.battery_stress_score,
            unit="/100",
            impact_level=stress.stress_level.value,
            comparison=stress.explanation,
        ),
        EvidenceItem(
            id="high_temperature_exposure",
            label="High temperature exposure",
            value=stress.high_temperature_exposure_percent,
            unit="%",
        ),
    ]


def build_anomaly_evidence(summary: IntelligenceSummary) -> List[EvidenceItem]:
    anomaly = summary.anomaly
    items = [
        EvidenceItem(
            id="anomaly_score",
            label="Anomaly score",
            value=anomaly.anomaly_score,
            unit="/100",
            impact_level=anomaly.severity.value,
            comparison="; ".join(anomaly.reasons) if anomaly.reasons else None,
        ),
    ]
    return items


def build_recommendations_evidence(summary: IntelligenceSummary) -> List[EvidenceItem]:
    return [
        EvidenceItem(
            id=f"recommendation_{r.id.value}",
            label=r.title,
            comparison=r.reason,
            impact_level=r.priority.value,
        )
        for r in summary.recommendations.recommendations
    ]


def build_drive_comparison_evidence(summary: IntelligenceSummary) -> List[EvidenceItem]:
    items = build_range_drop_evidence(summary)
    items.append(
        EvidenceItem(
            id="baseline_match",
            label="Comparison baseline",
            comparison=summary.baseline_match_type.value,
        )
    )
    return items


def build_general_vehicle_evidence(vehicle_summary: VehicleSummary) -> List[EvidenceItem]:
    vehicle = vehicle_summary.vehicle
    return [
        EvidenceItem(id="make_model", label="Vehicle", comparison=f"{vehicle.make} {vehicle.model} ({vehicle.model_year})"),
        EvidenceItem(
            id="battery",
            label="Battery",
            value=vehicle.usable_battery_capacity_kwh,
            unit="kWh usable",
            comparison=vehicle.battery_type,
        ),
        EvidenceItem(
            id="latest_scenario",
            label="Latest simulated drive",
            comparison=vehicle_summary.intelligence.observed_scenario,
        ),
    ]


def build_cost_evidence(result: CostAnalysisResult) -> List[EvidenceItem]:
    return [
        EvidenceItem(id="energy_cost", label="Energy cost", value=result.energy_cost_inr, unit="INR"),
        EvidenceItem(
            id="total_operating_cost",
            label="Total operating cost",
            value=result.total_operating_cost_inr,
            unit="INR",
        ),
        EvidenceItem(
            id="cost_per_km",
            label="Cost per km",
            value=result.cost_per_km_inr,
            unit="INR/km",
        ),
    ]


def build_what_if_evidence(result: WhatIfResult) -> List[EvidenceItem]:
    return [
        EvidenceItem(
            id="base_range",
            label=f"Your drive ({result.base_scenario})",
            value=result.base_metrics.estimated_range_km,
            unit="km",
        ),
        EvidenceItem(
            id="counterfactual_range",
            label=f"Counterfactual ({result.counterfactual_scenario})",
            value=result.counterfactual_metrics.estimated_range_km,
            unit="km",
        ),
        EvidenceItem(
            id="range_change",
            label="Estimated range difference",
            value=result.estimated_range_change_km,
            unit="km",
            direction=(
                "higher"
                if (result.estimated_range_change_km or 0) > 0
                else "lower"
                if (result.estimated_range_change_km or 0) < 0
                else None
            ),
        ),
    ]


def actions_for_intent(intent: Intent) -> List[ActionItem]:
    """Fixed, deterministic candidate actions per intent. The LLM may only
    choose among these by id -- it can never invent a new action."""
    mapping: dict[Intent, List[ActionItem]] = {
        Intent.RANGE_DROP: [
            ActionItem(id="WHAT_IF_NORMAL", label="What if I drove normally?", type=ActionType.WHAT_IF),
            ActionItem(id="VIEW_CONTRIBUTORS", label="See main contributors", type=ActionType.VIEW_CONTRIBUTORS),
            ActionItem(id="VIEW_RECOMMENDATIONS", label="See recommendations", type=ActionType.VIEW_RECOMMENDATIONS),
        ],
        Intent.ENERGY_EFFICIENCY: [
            ActionItem(id="VIEW_DRIVE", label="See drive details", type=ActionType.VIEW_DRIVE),
        ],
        Intent.BATTERY_STRESS: [
            ActionItem(id="VIEW_BATTERY", label="See battery details", type=ActionType.VIEW_BATTERY),
        ],
        Intent.ANOMALY: [
            ActionItem(id="VIEW_CONTRIBUTORS", label="See main contributors", type=ActionType.VIEW_CONTRIBUTORS),
        ],
        Intent.RECOMMENDATIONS: [
            ActionItem(id="VIEW_RECOMMENDATIONS", label="See all recommendations", type=ActionType.VIEW_RECOMMENDATIONS),
        ],
        Intent.DRIVE_COMPARISON: [
            ActionItem(id="WHAT_IF_NORMAL", label="What if I drove normally?", type=ActionType.WHAT_IF),
        ],
        Intent.GENERAL_VEHICLE: [
            ActionItem(id="VIEW_DRIVE", label="See latest drive", type=ActionType.VIEW_DRIVE),
        ],
        Intent.WHAT_IF: [],
        Intent.COST: [],
        Intent.UNKNOWN: [],
    }
    return mapping.get(intent, [])


OPEN_COST_ACTION = ActionItem(id="OPEN_COST", label="Calculate drive cost", type=ActionType.VIEW_COST)
