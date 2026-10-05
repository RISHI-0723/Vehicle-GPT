"""Intelligence API routes.

These endpoints provide deterministic vehicle intelligence analysis.
All endpoints are SIDE-EFFECT FREE - they do not modify simulation
or telemetry data.
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.db.database import get_db
from app.db.models import Vehicle, Simulation, Telemetry
from app.schemas.intelligence import (
    EnergyAnalysisResponse,
    RangeEstimationResponse,
    ContributorResponse,
    ContributorAnalysisResponse,
    AnomalyComponentResponse,
    AnomalyDetectionResponse,
    StressComponentResponse,
    BatteryStressResponse,
    WhatIfRequest,
    WhatIfMetricsResponse,
    WhatIfResponse,
    CostRequest,
    CostResponse,
    RecommendationResponse,
    RecommendationsResponse,
    ExplanationResponse,
    WhyRangeDroppedResponse,
    IntelligenceSummaryResponse,
    BaselineMatchType,
    ConfidenceLevel,
)
from app.intelligence.config import DEFAULT_CONFIG
from app.intelligence.features import FeatureExtractor
from app.intelligence.baseline import BaselineSelector
from app.intelligence.energy import EnergyAnalyzer
from app.intelligence.range_estimator import RangeEstimator
from app.intelligence.contributors import ContributorAnalyzer
from app.intelligence.anomaly import AnomalyDetector
from app.intelligence.battery_stress import BatteryStressAnalyzer
from app.intelligence.what_if import WhatIfEngine
from app.intelligence.cost import CostAnalyzer
from app.intelligence.recommendations import RecommendationEngine
from app.intelligence.orchestrator import IntelligenceOrchestrator

router = APIRouter(prefix="/api/v1/intelligence", tags=["intelligence"])

# Scenarios suitable for driving analysis
DRIVING_SCENARIOS = {"NORMAL_DRIVING", "HOT_INDIAN_DAY", "AGGRESSIVE_DRIVING", "ENERGY_ANOMALY"}


def get_vehicle_or_404(db: Session, vehicle_id: str) -> Vehicle:
    """Get vehicle or raise 404."""
    vehicle = db.query(Vehicle).filter(Vehicle.vehicle_id == vehicle_id).first()
    if not vehicle:
        raise HTTPException(status_code=404, detail=f"Vehicle not found: {vehicle_id}")
    return vehicle


def get_latest_driving_simulation(db: Session, vehicle_id: str) -> Simulation:
    """Get latest suitable driving simulation or raise 404."""
    sim = (
        db.query(Simulation)
        .filter(Simulation.vehicle_id == vehicle_id)
        .filter(Simulation.scenario.in_(DRIVING_SCENARIOS))
        .order_by(desc(Simulation.created_at))
        .first()
    )
    if not sim:
        raise HTTPException(
            status_code=404,
            detail=f"No suitable driving simulation found for vehicle: {vehicle_id}"
        )
    return sim


def get_simulation_telemetry(db: Session, simulation_id: str):
    """Get telemetry for a simulation."""
    return (
        db.query(Telemetry)
        .filter(Telemetry.simulation_id == simulation_id)
        .order_by(Telemetry.timestamp)
        .all()
    )


@router.get(
    "/energy/{vehicle_id}",
    response_model=EnergyAnalysisResponse,
    summary="Energy Analysis",
    description="Analyze energy consumption and efficiency for the latest driving simulation.",
)
def get_energy_analysis(
    vehicle_id: str,
    simulation_id: Optional[str] = Query(None, description="Specific simulation to analyze"),
    db: Session = Depends(get_db),
):
    """Get energy analysis for a vehicle's driving session."""
    get_vehicle_or_404(db, vehicle_id)

    # Get simulation
    if simulation_id:
        sim = db.query(Simulation).filter(Simulation.simulation_id == simulation_id).first()
        if not sim:
            raise HTTPException(status_code=404, detail=f"Simulation not found: {simulation_id}")
    else:
        sim = get_latest_driving_simulation(db, vehicle_id)

    # Get telemetry
    telemetry = get_simulation_telemetry(db, sim.simulation_id)
    if not telemetry:
        raise HTTPException(status_code=404, detail="No telemetry found for simulation")

    # Extract features
    extractor = FeatureExtractor(DEFAULT_CONFIG)
    features = extractor.extract(telemetry)

    # Get baseline
    selector = BaselineSelector(db)
    baseline_result = selector.select_baseline(vehicle_id, sim.duration_minutes, sim.interval_seconds)

    baseline_features = None
    if baseline_result.is_available and baseline_result.telemetry:
        baseline_features = extractor.extract(baseline_result.telemetry)

    # Analyze
    analyzer = EnergyAnalyzer(DEFAULT_CONFIG)
    result = analyzer.analyze(features, baseline_features)

    return EnergyAnalysisResponse(
        **result.__dict__,
        baseline_simulation_id=baseline_result.simulation_id,
        baseline_match_type=BaselineMatchType(baseline_result.match_type.value),
    )


@router.get(
    "/range/{vehicle_id}",
    response_model=RangeEstimationResponse,
    summary="Range Estimation",
    description="Estimate remaining driving range based on current SOC and recent efficiency.",
)
def get_range_estimation(
    vehicle_id: str,
    simulation_id: Optional[str] = Query(None, description="Specific simulation for efficiency"),
    db: Session = Depends(get_db),
):
    """Get range estimation for a vehicle."""
    get_vehicle_or_404(db, vehicle_id)

    # Get simulation for efficiency data
    if simulation_id:
        sim = db.query(Simulation).filter(Simulation.simulation_id == simulation_id).first()
        if not sim:
            raise HTTPException(status_code=404, detail=f"Simulation not found: {simulation_id}")
    else:
        sim = get_latest_driving_simulation(db, vehicle_id)

    # Get telemetry
    telemetry = get_simulation_telemetry(db, sim.simulation_id)
    if not telemetry:
        raise HTTPException(status_code=404, detail="No telemetry found for simulation")

    # Extract features
    extractor = FeatureExtractor(DEFAULT_CONFIG)
    features = extractor.extract(telemetry)

    # Get baseline for fallback efficiency
    selector = BaselineSelector(db)
    baseline_result = selector.select_baseline(vehicle_id, sim.duration_minutes, sim.interval_seconds)

    baseline_features = None
    if baseline_result.is_available and baseline_result.telemetry:
        baseline_features = extractor.extract(baseline_result.telemetry)

    # Estimate range
    estimator = RangeEstimator(DEFAULT_CONFIG)
    result = estimator.estimate(
        current_soc_percent=features.ending_soc_percent,
        observed_features=features,
        baseline_features=baseline_features,
    )

    return RangeEstimationResponse(
        current_soc_percent=result.current_soc_percent,
        remaining_energy_kwh=result.remaining_energy_kwh,
        efficiency_kwh_per_km=result.efficiency_kwh_per_km,
        efficiency_source=result.efficiency_source,
        estimated_range_km=result.estimated_range_km,
        confidence=ConfidenceLevel(result.confidence.value),
        confidence_reason=result.confidence_reason,
        disclaimer=result.disclaimer,
    )


@router.get(
    "/contributors/{vehicle_id}",
    response_model=ContributorAnalysisResponse,
    summary="Contributor Analysis",
    description="Analyze factors contributing to efficiency differences from baseline.",
)
def get_contributor_analysis(
    vehicle_id: str,
    simulation_id: Optional[str] = Query(None, description="Specific simulation to analyze"),
    db: Session = Depends(get_db),
):
    """Get contributor analysis for a vehicle's driving session."""
    get_vehicle_or_404(db, vehicle_id)

    # Get simulation
    if simulation_id:
        sim = db.query(Simulation).filter(Simulation.simulation_id == simulation_id).first()
        if not sim:
            raise HTTPException(status_code=404, detail=f"Simulation not found: {simulation_id}")
    else:
        sim = get_latest_driving_simulation(db, vehicle_id)

    # Get telemetry
    telemetry = get_simulation_telemetry(db, sim.simulation_id)
    if not telemetry:
        raise HTTPException(status_code=404, detail="No telemetry found for simulation")

    # Extract features
    extractor = FeatureExtractor(DEFAULT_CONFIG)
    features = extractor.extract(telemetry)

    # Get baseline
    selector = BaselineSelector(db)
    baseline_result = selector.select_baseline(vehicle_id, sim.duration_minutes, sim.interval_seconds)

    baseline_features = None
    if baseline_result.is_available and baseline_result.telemetry:
        baseline_features = extractor.extract(baseline_result.telemetry)

    # Analyze
    analyzer = ContributorAnalyzer(DEFAULT_CONFIG)
    result = analyzer.analyze(features, baseline_features)

    return ContributorAnalysisResponse(
        contributors=[
            ContributorResponse(
                id=c.id,
                name=c.name,
                observed_value=c.observed_value,
                baseline_value=c.baseline_value,
                difference=c.difference,
                difference_percent=c.difference_percent,
                impact_score=c.impact_score,
                impact_level=c.impact_level.value,
                description=c.description,
                is_available=c.is_available,
            )
            for c in result.contributors
        ],
        total_contributors=result.total_contributors,
        available_contributors=result.available_contributors,
        baseline_available=result.baseline_available,
        baseline_simulation_id=baseline_result.simulation_id,
        baseline_match_type=BaselineMatchType(baseline_result.match_type.value),
        summary=result.summary,
    )


@router.get(
    "/anomaly/{vehicle_id}",
    response_model=AnomalyDetectionResponse,
    summary="Anomaly Detection",
    description="Detect energy consumption anomalies compared to baseline.",
)
def get_anomaly_detection(
    vehicle_id: str,
    simulation_id: Optional[str] = Query(None, description="Specific simulation to analyze"),
    db: Session = Depends(get_db),
):
    """Get anomaly detection for a vehicle's driving session."""
    get_vehicle_or_404(db, vehicle_id)

    # Get simulation
    if simulation_id:
        sim = db.query(Simulation).filter(Simulation.simulation_id == simulation_id).first()
        if not sim:
            raise HTTPException(status_code=404, detail=f"Simulation not found: {simulation_id}")
    else:
        sim = get_latest_driving_simulation(db, vehicle_id)

    # Get telemetry
    telemetry = get_simulation_telemetry(db, sim.simulation_id)
    if not telemetry:
        raise HTTPException(status_code=404, detail="No telemetry found for simulation")

    # Extract features
    extractor = FeatureExtractor(DEFAULT_CONFIG)
    features = extractor.extract(telemetry)

    # Get baseline
    selector = BaselineSelector(db)
    baseline_result = selector.select_baseline(vehicle_id, sim.duration_minutes, sim.interval_seconds)

    baseline_features = None
    if baseline_result.is_available and baseline_result.telemetry:
        baseline_features = extractor.extract(baseline_result.telemetry)

    # Detect
    detector = AnomalyDetector(DEFAULT_CONFIG)
    result = detector.detect(features, baseline_features)

    return AnomalyDetectionResponse(
        anomaly_score=result.anomaly_score,
        severity=result.severity.value,
        is_anomalous=result.is_anomalous,
        reasons=result.reasons,
        components=[
            AnomalyComponentResponse(
                name=c.name,
                observed_value=c.observed_value,
                baseline_value=c.baseline_value,
                deviation_ratio=c.deviation_ratio,
                weighted_contribution=c.weighted_contribution,
                weight=c.weight,
                description=c.description,
            )
            for c in result.components
        ],
        baseline_available=result.baseline_available,
        baseline_simulation_id=baseline_result.simulation_id if baseline_result.is_available else None,
        baseline_match_type=BaselineMatchType(baseline_result.match_type.value),
        confidence=result.confidence,
    )


@router.get(
    "/battery-stress/{vehicle_id}",
    response_model=BatteryStressResponse,
    summary="Battery Stress Analysis",
    description="Analyze operational battery stress during a driving session.",
)
def get_battery_stress(
    vehicle_id: str,
    simulation_id: Optional[str] = Query(None, description="Specific simulation to analyze"),
    db: Session = Depends(get_db),
):
    """Get battery stress analysis for a vehicle's session."""
    get_vehicle_or_404(db, vehicle_id)

    # Get simulation
    if simulation_id:
        sim = db.query(Simulation).filter(Simulation.simulation_id == simulation_id).first()
        if not sim:
            raise HTTPException(status_code=404, detail=f"Simulation not found: {simulation_id}")
    else:
        sim = get_latest_driving_simulation(db, vehicle_id)

    # Get telemetry
    telemetry = get_simulation_telemetry(db, sim.simulation_id)
    if not telemetry:
        raise HTTPException(status_code=404, detail="No telemetry found for simulation")

    # Extract features
    extractor = FeatureExtractor(DEFAULT_CONFIG)
    features = extractor.extract(telemetry)

    # Analyze
    analyzer = BatteryStressAnalyzer(DEFAULT_CONFIG)
    result = analyzer.analyze(features)

    return BatteryStressResponse(
        battery_stress_score=result.battery_stress_score,
        stress_level=result.stress_level.value,
        components=[
            StressComponentResponse(
                name=c.name,
                raw_score=c.raw_score,
                weight=c.weight,
                weighted_score=c.weighted_score,
                description=c.description,
            )
            for c in result.components
        ],
        explanation=result.explanation,
        c_rate_average=result.c_rate_average,
        c_rate_max=result.c_rate_max,
        high_temperature_exposure_percent=result.high_temperature_exposure_percent,
        disclaimer=result.disclaimer,
    )


@router.get(
    "/recommendations/{vehicle_id}",
    response_model=RecommendationsResponse,
    summary="Recommendations",
    description="Get actionable recommendations based on the latest driving session.",
)
def get_recommendations(
    vehicle_id: str,
    simulation_id: Optional[str] = Query(None, description="Specific simulation to analyze"),
    db: Session = Depends(get_db),
):
    """Get recommendations for a vehicle."""
    get_vehicle_or_404(db, vehicle_id)

    # Get simulation
    if simulation_id:
        sim = db.query(Simulation).filter(Simulation.simulation_id == simulation_id).first()
        if not sim:
            raise HTTPException(status_code=404, detail=f"Simulation not found: {simulation_id}")
    else:
        sim = get_latest_driving_simulation(db, vehicle_id)

    # Get telemetry
    telemetry = get_simulation_telemetry(db, sim.simulation_id)
    if not telemetry:
        raise HTTPException(status_code=404, detail="No telemetry found for simulation")

    # Extract features
    extractor = FeatureExtractor(DEFAULT_CONFIG)
    features = extractor.extract(telemetry)

    # Get baseline for anomaly/contributor context
    selector = BaselineSelector(db)
    baseline_result = selector.select_baseline(vehicle_id, sim.duration_minutes, sim.interval_seconds)

    baseline_features = None
    if baseline_result.is_available and baseline_result.telemetry:
        baseline_features = extractor.extract(baseline_result.telemetry)

    # Get anomaly result for recommendations
    detector = AnomalyDetector(DEFAULT_CONFIG)
    anomaly_result = detector.detect(features, baseline_features)

    # Get stress result
    stress_analyzer = BatteryStressAnalyzer(DEFAULT_CONFIG)
    stress_result = stress_analyzer.analyze(features)

    # Generate recommendations
    engine = RecommendationEngine(DEFAULT_CONFIG)
    result = engine.generate(
        features=features,
        anomaly_result=anomaly_result,
        stress_result=stress_result,
    )

    return RecommendationsResponse(
        recommendations=[
            RecommendationResponse(
                id=r.id.value,
                title=r.title,
                priority=r.priority.value,
                reason=r.reason,
                expected_benefit=r.expected_benefit,
                related_metric=r.related_metric,
                impact_score=r.impact_score,
            )
            for r in result.recommendations
        ],
        total_generated=result.total_generated,
        total_returned=result.total_returned,
    )


@router.post(
    "/what-if",
    response_model=WhatIfResponse,
    summary="What-If Analysis",
    description="Run a counterfactual analysis. Example: 'What if I drove normally?'",
)
def run_what_if_analysis(
    request: WhatIfRequest,
    db: Session = Depends(get_db),
):
    """Run what-if counterfactual analysis."""
    engine = WhatIfEngine(db, DEFAULT_CONFIG)

    try:
        result = engine.run_counterfactual(
            vehicle_id=request.vehicle_id,
            counterfactual_scenario=request.counterfactual_scenario,
            base_simulation_id=request.base_simulation_id,
            duration_minutes=request.duration_minutes,
            interval_seconds=request.interval_seconds,
            seed=request.seed,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    return WhatIfResponse(
        base_simulation_id=result.base_simulation_id,
        base_scenario=result.base_scenario,
        counterfactual_scenario=result.counterfactual_scenario,
        starting_soc_percent=result.starting_soc_percent,
        base_metrics=WhatIfMetricsResponse(
            scenario=result.base_metrics.scenario,
            starting_soc_percent=result.base_metrics.starting_soc_percent,
            ending_soc_percent=result.base_metrics.ending_soc_percent,
            energy_consumed_kwh=result.base_metrics.energy_consumed_kwh,
            distance_km=result.base_metrics.distance_km,
            efficiency_kwh_per_100km=result.base_metrics.efficiency_kwh_per_100km,
            estimated_range_km=result.base_metrics.estimated_range_km,
            duration_seconds=result.base_metrics.duration_seconds,
            sample_count=result.base_metrics.sample_count,
        ),
        counterfactual_metrics=WhatIfMetricsResponse(
            scenario=result.counterfactual_metrics.scenario,
            starting_soc_percent=result.counterfactual_metrics.starting_soc_percent,
            ending_soc_percent=result.counterfactual_metrics.ending_soc_percent,
            energy_consumed_kwh=result.counterfactual_metrics.energy_consumed_kwh,
            distance_km=result.counterfactual_metrics.distance_km,
            efficiency_kwh_per_100km=result.counterfactual_metrics.efficiency_kwh_per_100km,
            estimated_range_km=result.counterfactual_metrics.estimated_range_km,
            duration_seconds=result.counterfactual_metrics.duration_seconds,
            sample_count=result.counterfactual_metrics.sample_count,
        ),
        energy_change_kwh=result.energy_change_kwh,
        energy_change_percent=result.energy_change_percent,
        estimated_range_change_km=result.estimated_range_change_km,
        interpretation=result.interpretation,
    )


@router.post(
    "/cost",
    response_model=CostResponse,
    summary="Cost Analysis",
    description="Calculate operating costs including energy and battery wear proxy.",
)
def calculate_cost(
    request: CostRequest,
    db: Session = Depends(get_db),
):
    """Calculate operating costs for a driving session."""
    get_vehicle_or_404(db, request.vehicle_id)

    # Get simulation
    if request.simulation_id:
        sim = db.query(Simulation).filter(Simulation.simulation_id == request.simulation_id).first()
        if not sim:
            raise HTTPException(status_code=404, detail=f"Simulation not found: {request.simulation_id}")
    else:
        sim = get_latest_driving_simulation(db, request.vehicle_id)

    # Get telemetry
    telemetry = get_simulation_telemetry(db, sim.simulation_id)
    if not telemetry:
        raise HTTPException(status_code=404, detail="No telemetry found for simulation")

    # Extract features
    extractor = FeatureExtractor(DEFAULT_CONFIG)
    features = extractor.extract(telemetry)

    # Get battery stress for wear calculation
    stress_analyzer = BatteryStressAnalyzer(DEFAULT_CONFIG)
    stress_result = stress_analyzer.analyze(features)

    # Calculate cost
    analyzer = CostAnalyzer(DEFAULT_CONFIG)
    try:
        result = analyzer.analyze(
            features=features,
            electricity_price_per_kwh=request.electricity_price_per_kwh,
            battery_stress_score=stress_result.battery_stress_score,
            battery_replacement_cost_per_kwh_inr=request.battery_replacement_cost_per_kwh_inr,
            wear_cost_fraction=request.wear_cost_fraction,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return CostResponse(
        energy_cost_inr=result.energy_cost_inr,
        electricity_price_per_kwh=result.electricity_price_per_kwh,
        energy_used_kwh=result.energy_used_kwh,
        wear_factor=result.wear_factor,
        estimated_battery_wear_cost_inr=result.estimated_battery_wear_cost_inr,
        total_operating_cost_inr=result.total_operating_cost_inr,
        cost_per_km_inr=result.cost_per_km_inr,
        distance_km=result.distance_km,
        duration_seconds=result.duration_seconds,
        disclaimer=result.disclaimer,
    )


@router.get(
    "/why-range-dropped/{vehicle_id}",
    response_model=WhyRangeDroppedResponse,
    summary="Why Did My Range Drop?",
    description=(
        "Comprehensive analysis explaining why estimated driving range "
        "differs from normal baseline. This is the hero intelligence endpoint."
    ),
)
def analyze_why_range_dropped(
    vehicle_id: str,
    simulation_id: Optional[str] = Query(None, description="Specific simulation to analyze"),
    db: Session = Depends(get_db),
):
    """Analyze why range dropped - the hero composite endpoint."""
    orchestrator = IntelligenceOrchestrator(db, DEFAULT_CONFIG)

    try:
        result = orchestrator.analyze_why_range_dropped(vehicle_id, simulation_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    # Convert to response schema
    return _build_composite_response(result)


@router.get(
    "/summary/{vehicle_id}",
    response_model=IntelligenceSummaryResponse,
    summary="Intelligence Summary",
    description="Get a complete intelligence summary for a vehicle's driving session.",
)
def get_intelligence_summary(
    vehicle_id: str,
    simulation_id: Optional[str] = Query(None, description="Specific simulation to analyze"),
    db: Session = Depends(get_db),
):
    """Get complete intelligence summary."""
    orchestrator = IntelligenceOrchestrator(db, DEFAULT_CONFIG)

    try:
        result = orchestrator.get_summary(vehicle_id, simulation_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    return _build_summary_response(result)


def _build_composite_response(result) -> WhyRangeDroppedResponse:
    """Build composite response from orchestrator result."""
    from app.intelligence.baseline import BaselineMatchType as InternalBaselineMatchType

    return WhyRangeDroppedResponse(
        vehicle_id=result.vehicle_id,
        observed_simulation_id=result.observed_simulation_id,
        observed_scenario=result.observed_scenario,
        baseline_simulation_id=result.baseline_simulation_id,
        baseline_match_type=BaselineMatchType(result.baseline_match_type.value),
        energy=_build_energy_response(result.energy, result.baseline_simulation_id, result.baseline_match_type),
        range_estimate=_build_range_response(result.range_estimate),
        contributors=_build_contributor_response(result.contributors, result.baseline_simulation_id, result.baseline_match_type),
        anomaly=_build_anomaly_response(result.anomaly, result.baseline_simulation_id, result.baseline_match_type),
        battery_stress=_build_stress_response(result.battery_stress),
        recommendations=_build_recommendations_response(result.recommendations),
        explanation=_build_explanation_response(result.explanation),
        confidence=ConfidenceLevel(result.confidence.value),
    )


def _build_summary_response(result) -> IntelligenceSummaryResponse:
    """Build summary response from orchestrator result."""
    return IntelligenceSummaryResponse(
        vehicle_id=result.vehicle_id,
        observed_simulation_id=result.observed_simulation_id,
        observed_scenario=result.observed_scenario,
        baseline_simulation_id=result.baseline_simulation_id,
        baseline_match_type=BaselineMatchType(result.baseline_match_type.value),
        energy=_build_energy_response(result.energy, result.baseline_simulation_id, result.baseline_match_type),
        range_estimate=_build_range_response(result.range_estimate),
        contributors=_build_contributor_response(result.contributors, result.baseline_simulation_id, result.baseline_match_type),
        anomaly=_build_anomaly_response(result.anomaly, result.baseline_simulation_id, result.baseline_match_type),
        battery_stress=_build_stress_response(result.battery_stress),
        recommendations=_build_recommendations_response(result.recommendations),
        explanation=_build_explanation_response(result.explanation),
        confidence=ConfidenceLevel(result.confidence.value),
    )


def _build_energy_response(result, baseline_id, baseline_match) -> EnergyAnalysisResponse:
    """Build energy analysis response."""
    return EnergyAnalysisResponse(
        energy_consumed_kwh=result.energy_consumed_kwh,
        energy_regenerated_kwh=result.energy_regenerated_kwh,
        net_energy_kwh=result.net_energy_kwh,
        distance_km=result.distance_km,
        energy_per_km=result.energy_per_km,
        efficiency_kwh_per_100km=result.efficiency_kwh_per_100km,
        regen_ratio=result.regen_ratio,
        baseline_efficiency_kwh_per_100km=result.baseline_efficiency_kwh_per_100km,
        efficiency_delta_kwh_per_100km=result.efficiency_delta_kwh_per_100km,
        efficiency_delta_percent=result.efficiency_delta_percent,
        rating=result.rating.value,
        rating_reason=result.rating_reason,
        duration_seconds=result.duration_seconds,
        sample_count=result.sample_count,
        baseline_simulation_id=baseline_id,
        baseline_match_type=BaselineMatchType(baseline_match.value),
    )


def _build_range_response(result) -> RangeEstimationResponse:
    """Build range estimation response."""
    return RangeEstimationResponse(
        current_soc_percent=result.current_soc_percent,
        remaining_energy_kwh=result.remaining_energy_kwh,
        efficiency_kwh_per_km=result.efficiency_kwh_per_km,
        efficiency_source=result.efficiency_source,
        estimated_range_km=result.estimated_range_km,
        confidence=ConfidenceLevel(result.confidence.value),
        confidence_reason=result.confidence_reason,
        disclaimer=result.disclaimer,
    )


def _build_contributor_response(result, baseline_id, baseline_match) -> ContributorAnalysisResponse:
    """Build contributor analysis response."""
    return ContributorAnalysisResponse(
        contributors=[
            ContributorResponse(
                id=c.id,
                name=c.name,
                observed_value=c.observed_value,
                baseline_value=c.baseline_value,
                difference=c.difference,
                difference_percent=c.difference_percent,
                impact_score=c.impact_score,
                impact_level=c.impact_level.value,
                description=c.description,
                is_available=c.is_available,
            )
            for c in result.contributors
        ],
        total_contributors=result.total_contributors,
        available_contributors=result.available_contributors,
        baseline_available=result.baseline_available,
        baseline_simulation_id=baseline_id,
        baseline_match_type=BaselineMatchType(baseline_match.value),
        summary=result.summary,
    )


def _build_anomaly_response(result, baseline_id, baseline_match) -> AnomalyDetectionResponse:
    """Build anomaly detection response."""
    return AnomalyDetectionResponse(
        anomaly_score=result.anomaly_score,
        severity=result.severity.value,
        is_anomalous=result.is_anomalous,
        reasons=result.reasons,
        components=[
            AnomalyComponentResponse(
                name=c.name,
                observed_value=c.observed_value,
                baseline_value=c.baseline_value,
                deviation_ratio=c.deviation_ratio,
                weighted_contribution=c.weighted_contribution,
                weight=c.weight,
                description=c.description,
            )
            for c in result.components
        ],
        baseline_available=result.baseline_available,
        baseline_simulation_id=baseline_id if result.baseline_available else None,
        baseline_match_type=BaselineMatchType(baseline_match.value),
        confidence=result.confidence,
    )


def _build_stress_response(result) -> BatteryStressResponse:
    """Build battery stress response."""
    return BatteryStressResponse(
        battery_stress_score=result.battery_stress_score,
        stress_level=result.stress_level.value,
        components=[
            StressComponentResponse(
                name=c.name,
                raw_score=c.raw_score,
                weight=c.weight,
                weighted_score=c.weighted_score,
                description=c.description,
            )
            for c in result.components
        ],
        explanation=result.explanation,
        c_rate_average=result.c_rate_average,
        c_rate_max=result.c_rate_max,
        high_temperature_exposure_percent=result.high_temperature_exposure_percent,
        disclaimer=result.disclaimer,
    )


def _build_recommendations_response(result) -> RecommendationsResponse:
    """Build recommendations response."""
    return RecommendationsResponse(
        recommendations=[
            RecommendationResponse(
                id=r.id.value,
                title=r.title,
                priority=r.priority.value,
                reason=r.reason,
                expected_benefit=r.expected_benefit,
                related_metric=r.related_metric,
                impact_score=r.impact_score,
            )
            for r in result.recommendations
        ],
        total_generated=result.total_generated,
        total_returned=result.total_returned,
    )


def _build_explanation_response(result) -> ExplanationResponse:
    """Build explanation response."""
    return ExplanationResponse(
        headline=result.headline,
        summary=result.summary,
        key_factors=result.key_factors,
        recommendation_summary=result.recommendation_summary,
        confidence=result.confidence,
    )
