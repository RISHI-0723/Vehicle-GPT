"""Pydantic schemas for intelligence API endpoints."""

from datetime import datetime
from typing import Optional, List
from enum import Enum
from pydantic import BaseModel, Field


# === Enums ===

class ConfidenceLevel(str, Enum):
    """Confidence level of intelligence analysis."""
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class EfficiencyRating(str, Enum):
    """Efficiency rating compared to baseline."""
    EFFICIENT = "EFFICIENT"
    NORMAL = "NORMAL"
    INEFFICIENT = "INEFFICIENT"
    UNKNOWN = "UNKNOWN"


class BaselineMatchType(str, Enum):
    """Type of baseline match found."""
    EXACT = "EXACT"
    APPROXIMATE = "APPROXIMATE"
    UNAVAILABLE = "UNAVAILABLE"


class ImpactLevel(str, Enum):
    """Impact level of a contributor."""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"
    UNAVAILABLE = "UNAVAILABLE"


class AnomalySeverity(str, Enum):
    """Severity of detected anomaly."""
    NORMAL = "NORMAL"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class StressLevel(str, Enum):
    """Battery stress level."""
    LOW = "LOW"
    MODERATE = "MODERATE"
    ELEVATED = "ELEVATED"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class RecommendationPriority(str, Enum):
    """Priority level for recommendations."""
    URGENT = "URGENT"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


# === Energy Analysis ===

class EnergyAnalysisResponse(BaseModel):
    """Response for energy analysis endpoint."""

    energy_consumed_kwh: float = Field(..., description="Total energy consumed")
    energy_regenerated_kwh: float = Field(..., description="Energy recovered via regeneration")
    net_energy_kwh: float = Field(..., description="Net energy (consumed - regenerated)")
    distance_km: float = Field(..., description="Total distance traveled")
    energy_per_km: Optional[float] = Field(None, description="Energy per kilometer")
    efficiency_kwh_per_100km: Optional[float] = Field(None, description="Efficiency in kWh/100km")
    regen_ratio: Optional[float] = Field(None, description="Regeneration ratio")
    baseline_efficiency_kwh_per_100km: Optional[float] = Field(None, description="Baseline efficiency")
    efficiency_delta_kwh_per_100km: Optional[float] = Field(None, description="Efficiency difference from baseline")
    efficiency_delta_percent: Optional[float] = Field(None, description="Efficiency difference percentage")
    rating: EfficiencyRating = Field(..., description="Efficiency rating")
    rating_reason: str = Field(..., description="Reason for rating")
    duration_seconds: float = Field(..., description="Analysis duration")
    sample_count: int = Field(..., description="Number of telemetry samples")
    baseline_simulation_id: Optional[str] = Field(None, description="Baseline simulation used")
    baseline_match_type: BaselineMatchType = Field(..., description="Type of baseline match")


# === Range Estimation ===

class RangeEstimationResponse(BaseModel):
    """Response for range estimation endpoint."""

    current_soc_percent: float = Field(..., description="Current battery SOC")
    remaining_energy_kwh: float = Field(..., description="Remaining usable energy")
    efficiency_kwh_per_km: Optional[float] = Field(None, description="Efficiency used for estimation")
    efficiency_source: str = Field(..., description="Source of efficiency data")
    estimated_range_km: Optional[float] = Field(None, description="Estimated remaining range")
    confidence: ConfidenceLevel = Field(..., description="Confidence level")
    confidence_reason: str = Field(..., description="Reason for confidence level")
    disclaimer: str = Field(..., description="Disclaimer about estimate")


# === Contributor Analysis ===

class ContributorResponse(BaseModel):
    """A single contributor to efficiency differences."""

    id: str = Field(..., description="Contributor identifier")
    name: str = Field(..., description="Human-readable name")
    observed_value: Optional[float] = Field(None, description="Observed value")
    baseline_value: Optional[float] = Field(None, description="Baseline value")
    difference: Optional[float] = Field(None, description="Absolute difference")
    difference_percent: Optional[float] = Field(None, description="Percentage difference")
    impact_score: float = Field(..., description="Impact score (0-100)")
    impact_level: ImpactLevel = Field(..., description="Impact level")
    description: str = Field(..., description="Description of this contributor")
    is_available: bool = Field(..., description="Whether comparison was possible")


class ContributorAnalysisResponse(BaseModel):
    """Response for contributor analysis endpoint."""

    contributors: List[ContributorResponse] = Field(..., description="List of contributors")
    total_contributors: int = Field(..., description="Total number of contributors analyzed")
    available_contributors: int = Field(..., description="Contributors with baseline comparison")
    baseline_available: bool = Field(..., description="Whether baseline was available")
    baseline_simulation_id: Optional[str] = Field(None, description="Baseline simulation used")
    baseline_match_type: BaselineMatchType = Field(..., description="Type of baseline match")
    summary: str = Field(..., description="Summary of contributor analysis")


# === Anomaly Detection ===

class AnomalyComponentResponse(BaseModel):
    """Individual component of anomaly score."""

    name: str = Field(..., description="Component name")
    observed_value: Optional[float] = Field(None, description="Observed value")
    baseline_value: Optional[float] = Field(None, description="Baseline value")
    deviation_ratio: float = Field(..., description="Deviation ratio (0-1)")
    weighted_contribution: float = Field(..., description="Weighted contribution to score")
    weight: float = Field(..., description="Weight of this component")
    description: str = Field(..., description="Description of component status")


class AnomalyDetectionResponse(BaseModel):
    """Response for anomaly detection endpoint."""

    anomaly_score: float = Field(..., description="Anomaly score (0-100)")
    severity: AnomalySeverity = Field(..., description="Anomaly severity")
    is_anomalous: bool = Field(..., description="Whether anomaly was detected")
    reasons: List[str] = Field(..., description="Reasons for anomaly")
    components: List[AnomalyComponentResponse] = Field(..., description="Score components")
    baseline_available: bool = Field(..., description="Whether baseline was available")
    baseline_simulation_id: Optional[str] = Field(None, description="Baseline simulation used")
    baseline_match_type: BaselineMatchType = Field(..., description="Type of baseline match")
    confidence: str = Field(..., description="Confidence level description")


# === Battery Stress ===

class StressComponentResponse(BaseModel):
    """Individual stress component."""

    name: str = Field(..., description="Component name")
    raw_score: float = Field(..., description="Raw score (0-100)")
    weight: float = Field(..., description="Weight of this component")
    weighted_score: float = Field(..., description="Weighted contribution")
    description: str = Field(..., description="Description of stress level")


class BatteryStressResponse(BaseModel):
    """Response for battery stress endpoint."""

    battery_stress_score: float = Field(..., description="Overall stress score (0-100)")
    stress_level: StressLevel = Field(..., description="Stress level category")
    components: List[StressComponentResponse] = Field(..., description="Stress components")
    explanation: str = Field(..., description="Explanation of stress analysis")
    c_rate_average: float = Field(..., description="Average C-rate during session")
    c_rate_max: float = Field(..., description="Maximum C-rate")
    high_temperature_exposure_percent: float = Field(..., description="Percentage of time at high temp")
    disclaimer: str = Field(..., description="Disclaimer about stress analysis")


# === What-If Analysis ===

class WhatIfRequest(BaseModel):
    """Request for what-if analysis."""

    vehicle_id: str = Field(..., description="Vehicle to analyze")
    counterfactual_scenario: str = Field(..., description="Alternative scenario to simulate")
    base_simulation_id: Optional[str] = Field(None, description="Base simulation (optional)")
    duration_minutes: Optional[int] = Field(None, description="Duration (inherits from base if not specified)")
    interval_seconds: Optional[int] = Field(None, description="Interval (inherits from base if not specified)")
    seed: int = Field(default=42, description="Random seed for counterfactual")


class WhatIfMetricsResponse(BaseModel):
    """Metrics for a single scenario in what-if analysis."""

    scenario: str = Field(..., description="Scenario name")
    starting_soc_percent: float = Field(..., description="Starting SOC")
    ending_soc_percent: float = Field(..., description="Ending SOC")
    energy_consumed_kwh: float = Field(..., description="Energy consumed")
    distance_km: float = Field(..., description="Distance traveled")
    efficiency_kwh_per_100km: Optional[float] = Field(None, description="Efficiency")
    estimated_range_km: Optional[float] = Field(None, description="Estimated remaining range")
    duration_seconds: float = Field(..., description="Duration in seconds")
    sample_count: int = Field(..., description="Number of samples")


class WhatIfResponse(BaseModel):
    """Response for what-if analysis endpoint."""

    base_simulation_id: str = Field(..., description="Base simulation analyzed")
    base_scenario: str = Field(..., description="Base scenario name")
    counterfactual_scenario: str = Field(..., description="Counterfactual scenario")
    starting_soc_percent: float = Field(..., description="Starting SOC (same for both)")
    base_metrics: WhatIfMetricsResponse = Field(..., description="Base scenario metrics")
    counterfactual_metrics: WhatIfMetricsResponse = Field(..., description="Counterfactual metrics")
    energy_change_kwh: Optional[float] = Field(None, description="Energy difference")
    energy_change_percent: Optional[float] = Field(None, description="Energy difference percentage")
    estimated_range_change_km: Optional[float] = Field(None, description="Range difference (null for charging)")
    interpretation: str = Field(..., description="Human-readable interpretation")


# === Cost Analysis ===

class CostRequest(BaseModel):
    """Request for cost analysis."""

    vehicle_id: str = Field(..., description="Vehicle to analyze")
    simulation_id: Optional[str] = Field(None, description="Specific simulation (optional)")
    electricity_price_per_kwh: float = Field(..., gt=0, description="Electricity price in INR per kWh")
    battery_replacement_cost_per_kwh_inr: Optional[float] = Field(
        None, description="Battery replacement cost per kWh (optional, default 10000)"
    )
    wear_cost_fraction: Optional[float] = Field(
        None, description="Wear cost fraction (optional, default 0.0001)"
    )


class CostResponse(BaseModel):
    """Response for cost analysis endpoint."""

    energy_cost_inr: float = Field(..., description="Energy cost in INR")
    electricity_price_per_kwh: float = Field(..., description="Electricity price used")
    energy_used_kwh: float = Field(..., description="Energy used for cost calculation")
    wear_factor: float = Field(..., description="Battery wear factor (0-1)")
    estimated_battery_wear_cost_inr: float = Field(..., description="Estimated battery wear cost")
    total_operating_cost_inr: float = Field(..., description="Total operating cost")
    cost_per_km_inr: Optional[float] = Field(None, description="Cost per kilometer")
    distance_km: float = Field(..., description="Distance traveled")
    duration_seconds: float = Field(..., description="Analysis duration")
    disclaimer: str = Field(..., description="Disclaimer about wear cost")


# === Recommendations ===

class RecommendationResponse(BaseModel):
    """A single recommendation."""

    id: str = Field(..., description="Recommendation identifier")
    title: str = Field(..., description="Recommendation title")
    priority: RecommendationPriority = Field(..., description="Priority level")
    reason: str = Field(..., description="Specific reason for this recommendation")
    expected_benefit: str = Field(..., description="Expected benefit")
    related_metric: str = Field(..., description="Related metric")
    impact_score: float = Field(..., description="Impact score (0-100)")


class RecommendationsResponse(BaseModel):
    """Response for recommendations endpoint."""

    recommendations: List[RecommendationResponse] = Field(..., description="List of recommendations")
    total_generated: int = Field(..., description="Total recommendations generated")
    total_returned: int = Field(..., description="Recommendations returned (max 5)")


# === Explanation ===

class ExplanationResponse(BaseModel):
    """Human-readable explanation."""

    headline: str = Field(..., description="Main headline")
    summary: str = Field(..., description="Summary paragraph")
    key_factors: List[str] = Field(..., description="Key contributing factors")
    recommendation_summary: str = Field(..., description="Summary of recommendations")
    confidence: str = Field(..., description="Confidence description")


# === Why Range Dropped (Composite) ===

class WhyRangeDroppedResponse(BaseModel):
    """Response for why-range-dropped composite endpoint."""

    # Metadata
    vehicle_id: str = Field(..., description="Vehicle analyzed")
    observed_simulation_id: str = Field(..., description="Observed simulation")
    observed_scenario: str = Field(..., description="Observed scenario")
    baseline_simulation_id: Optional[str] = Field(None, description="Baseline simulation")
    baseline_match_type: BaselineMatchType = Field(..., description="Baseline match type")

    # Analysis results
    energy: EnergyAnalysisResponse = Field(..., description="Energy analysis")
    range_estimate: RangeEstimationResponse = Field(..., description="Range estimation")
    contributors: ContributorAnalysisResponse = Field(..., description="Contributor analysis")
    anomaly: AnomalyDetectionResponse = Field(..., description="Anomaly detection")
    battery_stress: BatteryStressResponse = Field(..., description="Battery stress analysis")
    recommendations: RecommendationsResponse = Field(..., description="Recommendations")
    explanation: ExplanationResponse = Field(..., description="Human-readable explanation")

    # Overall confidence
    confidence: ConfidenceLevel = Field(..., description="Overall confidence level")


# === Intelligence Summary ===

class IntelligenceSummaryResponse(BaseModel):
    """Response for intelligence summary endpoint."""

    vehicle_id: str = Field(..., description="Vehicle analyzed")
    observed_simulation_id: str = Field(..., description="Observed simulation")
    observed_scenario: str = Field(..., description="Observed scenario")
    baseline_simulation_id: Optional[str] = Field(None, description="Baseline simulation")
    baseline_match_type: BaselineMatchType = Field(..., description="Baseline match type")
    energy: EnergyAnalysisResponse = Field(..., description="Energy analysis")
    range_estimate: RangeEstimationResponse = Field(..., description="Range estimation")
    contributors: ContributorAnalysisResponse = Field(..., description="Contributor analysis")
    anomaly: AnomalyDetectionResponse = Field(..., description="Anomaly detection")
    battery_stress: BatteryStressResponse = Field(..., description="Battery stress analysis")
    recommendations: RecommendationsResponse = Field(..., description="Recommendations")
    explanation: ExplanationResponse = Field(..., description="Human-readable explanation")
    confidence: ConfidenceLevel = Field(..., description="Overall confidence level")
