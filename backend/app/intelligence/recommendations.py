"""Recommendation engine.

This module generates actionable recommendations based on
intelligence analysis outputs.

SAFETY NOTE: Recommendations are efficiency/awareness guidance.
They do NOT include unsafe driving instructions.
"""

from dataclasses import dataclass
from enum import Enum
from typing import List, Optional

from app.intelligence.config import IntelligenceConfig, DEFAULT_CONFIG
from app.intelligence.features import TelemetryFeatures
from app.intelligence.anomaly import AnomalyDetectionResult
from app.intelligence.battery_stress import BatteryStressResult
from app.intelligence.contributors import ContributorAnalysisResult


class RecommendationPriority(str, Enum):
    """Priority level for recommendations."""

    URGENT = "URGENT"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class RecommendationId(str, Enum):
    """Standard recommendation identifiers."""

    REDUCE_SPEED = "REDUCE_SPEED"
    SMOOTHER_ACCELERATION = "SMOOTHER_ACCELERATION"
    REDUCE_HIGH_TEMP_EXPOSURE = "REDUCE_HIGH_TEMP_EXPOSURE"
    REDUCE_HIGH_POWER_LOAD = "REDUCE_HIGH_POWER_LOAD"
    USE_REGEN_EFFECTIVELY = "USE_REGEN_EFFECTIVELY"
    AVOID_DEEP_SOC_SWINGS = "AVOID_DEEP_SOC_SWINGS"
    REDUCE_FAST_CHARGING_STRESS = "REDUCE_FAST_CHARGING_STRESS"
    CHECK_ENERGY_ANOMALY = "CHECK_ENERGY_ANOMALY"


@dataclass
class Recommendation:
    """A single recommendation."""

    id: RecommendationId
    title: str
    priority: RecommendationPriority
    reason: str
    expected_benefit: str
    related_metric: str
    impact_score: float  # 0-100


@dataclass
class RecommendationResult:
    """Result of recommendation analysis."""

    recommendations: List[Recommendation]
    total_generated: int
    total_returned: int  # After dedup and limit


class RecommendationEngine:
    """Generates recommendations from intelligence outputs.

    Rules:
    - Recommendations are deterministic
    - Deduplicated by id
    - Maximum 5 recommendations
    - Ordered by priority, then by impact_score

    SAFETY: Never recommends:
    - Speeding
    - Dangerous acceleration
    - Unsafe braking
    - Driving while distracted
    - Ignoring battery warnings
    """

    # Recommendation definitions
    RECOMMENDATIONS = {
        RecommendationId.REDUCE_SPEED: {
            "title": "Consider Reducing Cruising Speed",
            "expected_benefit": "Lower air resistance improves efficiency by 5-15%",
            "related_metric": "average_speed_kmh",
        },
        RecommendationId.SMOOTHER_ACCELERATION: {
            "title": "Use Smoother Acceleration",
            "expected_benefit": "Gradual acceleration can improve efficiency by 10-20%",
            "related_metric": "aggressive_driving_score",
        },
        RecommendationId.REDUCE_HIGH_TEMP_EXPOSURE: {
            "title": "Reduce Battery High-Temperature Exposure",
            "expected_benefit": "Lower temperatures reduce operational stress",
            "related_metric": "battery_temperature_max_c",
        },
        RecommendationId.REDUCE_HIGH_POWER_LOAD: {
            "title": "Moderate High Power Demands",
            "expected_benefit": "Lower peak power reduces battery stress",
            "related_metric": "battery_power_peak_kw",
        },
        RecommendationId.USE_REGEN_EFFECTIVELY: {
            "title": "Maximize Regenerative Braking",
            "expected_benefit": "Better regen can recover 10-20% more energy",
            "related_metric": "regen_ratio",
        },
        RecommendationId.AVOID_DEEP_SOC_SWINGS: {
            "title": "Avoid Deep Discharge Cycles",
            "expected_benefit": "Keeping SOC between 20-80% reduces stress",
            "related_metric": "soc_swing_percent",
        },
        RecommendationId.REDUCE_FAST_CHARGING_STRESS: {
            "title": "Reduce Frequent Fast Charging",
            "expected_benefit": "Occasional fast charging is fine; frequent use increases stress",
            "related_metric": "estimated_c_rate_average",
        },
        RecommendationId.CHECK_ENERGY_ANOMALY: {
            "title": "Investigate Energy Anomaly",
            "expected_benefit": "Addressing the cause can restore normal efficiency",
            "related_metric": "anomaly_score",
        },
    }

    def __init__(self, config: IntelligenceConfig = DEFAULT_CONFIG):
        """Initialize recommendation engine.

        Args:
            config: Intelligence configuration
        """
        self.config = config

    def generate(
        self,
        features: TelemetryFeatures,
        anomaly_result: Optional[AnomalyDetectionResult] = None,
        stress_result: Optional[BatteryStressResult] = None,
        contributor_result: Optional[ContributorAnalysisResult] = None,
    ) -> RecommendationResult:
        """Generate recommendations from intelligence outputs.

        Args:
            features: Extracted telemetry features
            anomaly_result: Anomaly detection result (optional)
            stress_result: Battery stress result (optional)
            contributor_result: Contributor analysis result (optional)

        Returns:
            RecommendationResult with up to 5 recommendations
        """
        recommendations: List[Recommendation] = []

        # Check speed-related recommendations
        if features.average_speed_kmh > self.config.high_speed_threshold_kmh:
            recommendations.append(self._create_recommendation(
                RecommendationId.REDUCE_SPEED,
                RecommendationPriority.MEDIUM,
                f"Average speed was {features.average_speed_kmh:.0f} km/h",
                self._calculate_speed_impact(features),
            ))

        # Check acceleration-related recommendations
        if (
            features.aggressive_driving_score_average > 30 or
            features.harsh_acceleration_count > 5
        ):
            recommendations.append(self._create_recommendation(
                RecommendationId.SMOOTHER_ACCELERATION,
                RecommendationPriority.MEDIUM,
                f"Aggressive driving score: {features.aggressive_driving_score_average:.0f}, "
                f"{features.harsh_acceleration_count} harsh acceleration events",
                self._calculate_acceleration_impact(features),
            ))

        # Check temperature recommendations
        if features.high_temperature_exposure_ratio > 0.2:
            priority = (
                RecommendationPriority.HIGH
                if features.battery_temperature_max_c > self.config.critical_temperature_threshold_c
                else RecommendationPriority.MEDIUM
            )
            recommendations.append(self._create_recommendation(
                RecommendationId.REDUCE_HIGH_TEMP_EXPOSURE,
                priority,
                f"Battery reached {features.battery_temperature_max_c:.0f}\u00b0C, "
                f"{features.high_temperature_exposure_ratio*100:.0f}% time at elevated temperature",
                self._calculate_temp_impact(features),
            ))

        # Check power recommendations
        if features.estimated_c_rate_max > self.config.critical_c_rate_threshold:
            recommendations.append(self._create_recommendation(
                RecommendationId.REDUCE_HIGH_POWER_LOAD,
                RecommendationPriority.MEDIUM,
                f"Peak C-rate was {features.estimated_c_rate_max:.2f}C",
                min(features.estimated_c_rate_max * 30, 80),
            ))

        # Check regen recommendations
        if features.regen_ratio is not None and features.regen_ratio < 0.1:
            recommendations.append(self._create_recommendation(
                RecommendationId.USE_REGEN_EFFECTIVELY,
                RecommendationPriority.LOW,
                f"Regen ratio was only {features.regen_ratio*100:.0f}%",
                40.0,
            ))

        # Check SOC swing recommendations
        if features.soc_swing_percent > 60:
            priority = (
                RecommendationPriority.HIGH
                if features.min_soc_percent < self.config.deep_discharge_threshold_percent
                else RecommendationPriority.MEDIUM
            )
            recommendations.append(self._create_recommendation(
                RecommendationId.AVOID_DEEP_SOC_SWINGS,
                priority,
                f"SOC swung from {features.min_soc_percent:.0f}% to {features.max_soc_percent:.0f}%",
                min(features.soc_swing_percent, 80),
            ))

        # Check charging stress recommendations
        if features.is_charging_session and features.estimated_c_rate_average > 1.5:
            recommendations.append(self._create_recommendation(
                RecommendationId.REDUCE_FAST_CHARGING_STRESS,
                RecommendationPriority.LOW,
                f"Charging at {features.estimated_c_rate_average:.1f}C average",
                min(features.estimated_c_rate_average * 25, 60),
            ))

        # Check anomaly recommendations
        if anomaly_result is not None and anomaly_result.is_anomalous:
            priority = (
                RecommendationPriority.URGENT
                if anomaly_result.anomaly_score >= 75
                else RecommendationPriority.HIGH
            )
            recommendations.append(self._create_recommendation(
                RecommendationId.CHECK_ENERGY_ANOMALY,
                priority,
                f"Energy anomaly detected with score {anomaly_result.anomaly_score:.0f}",
                anomaly_result.anomaly_score,
            ))

        # Deduplicate by id
        seen_ids = set()
        unique_recommendations = []
        for rec in recommendations:
            if rec.id not in seen_ids:
                seen_ids.add(rec.id)
                unique_recommendations.append(rec)

        # Sort by priority (URGENT > HIGH > MEDIUM > LOW), then by impact_score
        priority_order = {
            RecommendationPriority.URGENT: 0,
            RecommendationPriority.HIGH: 1,
            RecommendationPriority.MEDIUM: 2,
            RecommendationPriority.LOW: 3,
        }
        unique_recommendations.sort(
            key=lambda r: (priority_order[r.priority], -r.impact_score)
        )

        # Limit to max recommendations
        total_generated = len(unique_recommendations)
        limited_recommendations = unique_recommendations[:self.config.max_recommendations]

        return RecommendationResult(
            recommendations=limited_recommendations,
            total_generated=total_generated,
            total_returned=len(limited_recommendations),
        )

    def _create_recommendation(
        self,
        rec_id: RecommendationId,
        priority: RecommendationPriority,
        reason: str,
        impact_score: float,
    ) -> Recommendation:
        """Create a recommendation from template.

        Args:
            rec_id: Recommendation ID
            priority: Priority level
            reason: Specific reason for this recommendation
            impact_score: Impact score (0-100)

        Returns:
            Recommendation object
        """
        template = self.RECOMMENDATIONS[rec_id]
        return Recommendation(
            id=rec_id,
            title=template["title"],
            priority=priority,
            reason=reason,
            expected_benefit=template["expected_benefit"],
            related_metric=template["related_metric"],
            impact_score=round(min(100, max(0, impact_score)), self.config.score_precision),
        )

    def _calculate_speed_impact(self, features: TelemetryFeatures) -> float:
        """Calculate impact score for speed recommendation."""
        excess = features.average_speed_kmh - self.config.high_speed_threshold_kmh
        return min(excess * 2, 60)

    def _calculate_acceleration_impact(self, features: TelemetryFeatures) -> float:
        """Calculate impact score for acceleration recommendation."""
        score = features.aggressive_driving_score_average
        harsh_factor = features.harsh_acceleration_count * 3
        return min(score + harsh_factor, 80)

    def _calculate_temp_impact(self, features: TelemetryFeatures) -> float:
        """Calculate impact score for temperature recommendation."""
        exposure = features.high_temperature_exposure_ratio * 100
        peak_excess = max(
            0,
            features.battery_temperature_max_c - self.config.high_temperature_threshold_c
        ) * 5
        return min(exposure + peak_excess, 90)
