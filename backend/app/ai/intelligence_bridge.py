"""Typed internal services the AI layer calls for vehicle intelligence.

Every function here delegates to the existing Sprint 2 engines
(IntelligenceOrchestrator, WhatIfEngine, CostAnalyzer, ...). No formula is
reimplemented. A ValueError from the underlying engine (no vehicle, no
suitable simulation, no telemetry) propagates unchanged -- app/ai/service.py
is responsible for turning that into a driver-friendly HTTP error, never a
fabricated AI answer.
"""
from dataclasses import dataclass
from typing import List, Optional

from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.db.models import Simulation, Telemetry, Vehicle
from app.intelligence.config import DEFAULT_CONFIG
from app.intelligence.cost import CostAnalysisResult, CostAnalyzer
from app.intelligence.orchestrator import IntelligenceOrchestrator, IntelligenceSummary
from app.intelligence.what_if import WhatIfEngine, WhatIfResult

# Scenarios suitable for driving (cost) analysis -- mirrors routes_intelligence.py
# and the engines above; this is a lookup, not a formula, so duplicating it here
# (as every other intelligence module already does) avoids importing route internals.
_DRIVING_SCENARIOS = {"NORMAL_DRIVING", "HOT_INDIAN_DAY", "AGGRESSIVE_DRIVING", "ENERGY_ANOMALY"}


def _find_latest_driving_simulation(db: Session, vehicle_id: str) -> Simulation:
    sim = (
        db.query(Simulation)
        .filter(Simulation.vehicle_id == vehicle_id)
        .filter(Simulation.scenario.in_(_DRIVING_SCENARIOS))
        .order_by(desc(Simulation.created_at))
        .first()
    )
    if not sim:
        raise ValueError(f"No suitable driving simulation found for vehicle: {vehicle_id}")
    return sim


def _get_simulation_telemetry(db: Session, simulation_id: str) -> List[Telemetry]:
    return (
        db.query(Telemetry)
        .filter(Telemetry.simulation_id == simulation_id)
        .order_by(Telemetry.timestamp)
        .all()
    )


@dataclass
class VehicleSummary:
    """Vehicle identity plus its latest-drive intelligence, for GENERAL_VEHICLE."""

    vehicle: Vehicle
    intelligence: IntelligenceSummary


def get_why_range_dropped(
    db: Session, vehicle_id: str, simulation_id: Optional[str] = None
) -> IntelligenceSummary:
    """The composite "why did my range drop" analysis. Raises ValueError if unavailable."""
    return IntelligenceOrchestrator(db, DEFAULT_CONFIG).analyze_why_range_dropped(vehicle_id, simulation_id)


# All of these intents are explained by different slices of the same composite
# summary, so they share one orchestrator call rather than re-deriving features
# and baselines independently.
get_energy_analysis = get_why_range_dropped
get_range_estimate = get_why_range_dropped
get_anomaly_analysis = get_why_range_dropped
get_battery_stress = get_why_range_dropped
get_contributors = get_why_range_dropped
get_recommendations = get_why_range_dropped


def get_vehicle_summary(
    db: Session, vehicle_id: str, simulation_id: Optional[str] = None
) -> VehicleSummary:
    """Vehicle identity (known, static config) plus its latest-drive intelligence."""
    vehicle = db.query(Vehicle).filter(Vehicle.vehicle_id == vehicle_id).first()
    if not vehicle:
        raise ValueError(f"Vehicle not found: {vehicle_id}")
    intelligence = get_why_range_dropped(db, vehicle_id, simulation_id)
    return VehicleSummary(vehicle=vehicle, intelligence=intelligence)


def run_what_if(
    db: Session,
    vehicle_id: str,
    scenario: str,
    base_simulation_id: Optional[str] = None,
    seed: int = 42,
    duration_minutes: Optional[int] = None,
    interval_seconds: Optional[int] = None,
) -> WhatIfResult:
    """Run a counterfactual simulation. base_simulation_id=None resolves the latest
    suitable driving simulation server-side -- the AI layer never supplies a UUID."""
    return WhatIfEngine(db, DEFAULT_CONFIG).run_counterfactual(
        vehicle_id=vehicle_id,
        counterfactual_scenario=scenario,
        base_simulation_id=base_simulation_id,
        duration_minutes=duration_minutes,
        interval_seconds=interval_seconds,
        seed=seed,
    )


def calculate_cost(
    db: Session,
    vehicle_id: str,
    simulation_id: Optional[str],
    electricity_price_per_kwh: float,
) -> CostAnalysisResult:
    """Calculate the operating cost of the given (or latest) simulation.

    The caller MUST already have a valid electricity_price_per_kwh -- this
    function never defaults or invents one.
    """
    from app.intelligence.battery_stress import BatteryStressAnalyzer
    from app.intelligence.features import FeatureExtractor

    vehicle = db.query(Vehicle).filter(Vehicle.vehicle_id == vehicle_id).first()
    if not vehicle:
        raise ValueError(f"Vehicle not found: {vehicle_id}")

    if simulation_id:
        sim = db.query(Simulation).filter(Simulation.simulation_id == simulation_id).first()
        if not sim:
            raise ValueError(f"Simulation not found: {simulation_id}")
    else:
        sim = _find_latest_driving_simulation(db, vehicle_id)

    telemetry = _get_simulation_telemetry(db, sim.simulation_id)
    if not telemetry:
        raise ValueError(f"No telemetry found for simulation: {sim.simulation_id}")

    extractor = FeatureExtractor(DEFAULT_CONFIG)
    features = extractor.extract(telemetry)

    stress_result = BatteryStressAnalyzer(DEFAULT_CONFIG).analyze(features)

    return CostAnalyzer(DEFAULT_CONFIG).analyze(
        features=features,
        electricity_price_per_kwh=electricity_price_per_kwh,
        battery_stress_score=stress_result.battery_stress_score,
    )
