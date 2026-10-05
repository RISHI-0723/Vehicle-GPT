"""Energy analysis service.

This module provides energy consumption and efficiency analysis
using the shared feature extraction pipeline.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional

from app.intelligence.config import IntelligenceConfig, DEFAULT_CONFIG
from app.intelligence.features import TelemetryFeatures


class EfficiencyRating(str, Enum):
    """Efficiency rating compared to baseline."""

    EFFICIENT = "EFFICIENT"
    NORMAL = "NORMAL"
    INEFFICIENT = "INEFFICIENT"
    UNKNOWN = "UNKNOWN"  # When baseline unavailable


@dataclass
class EnergyAnalysisResult:
    """Result of energy analysis."""

    # Core energy metrics
    energy_consumed_kwh: float
    energy_regenerated_kwh: float
    net_energy_kwh: float

    # Distance and efficiency
    distance_km: float
    energy_per_km: Optional[float]
    efficiency_kwh_per_100km: Optional[float]

    # Regeneration
    regen_ratio: Optional[float]  # regen / consumed

    # Comparison with baseline (if available)
    baseline_efficiency_kwh_per_100km: Optional[float]
    efficiency_delta_kwh_per_100km: Optional[float]
    efficiency_delta_percent: Optional[float]

    # Rating
    rating: EfficiencyRating
    rating_reason: str

    # Metadata
    duration_seconds: float
    sample_count: int


class EnergyAnalyzer:
    """Analyzes energy consumption and efficiency.

    This analyzer uses the shared feature extraction pipeline
    and optionally compares against a baseline for rating.
    """

    # Efficiency comparison thresholds (as percentage)
    EFFICIENT_THRESHOLD_PERCENT = -5.0  # 5% better than baseline = efficient
    INEFFICIENT_THRESHOLD_PERCENT = 10.0  # 10% worse than baseline = inefficient

    def __init__(self, config: IntelligenceConfig = DEFAULT_CONFIG):
        """Initialize energy analyzer.

        Args:
            config: Intelligence configuration
        """
        self.config = config

    def analyze(
        self,
        features: TelemetryFeatures,
        baseline_features: Optional[TelemetryFeatures] = None,
    ) -> EnergyAnalysisResult:
        """Analyze energy metrics from extracted features.

        Args:
            features: Extracted features from observed telemetry
            baseline_features: Extracted features from baseline (optional)

        Returns:
            EnergyAnalysisResult with energy metrics and comparison
        """
        # Extract baseline efficiency if available
        baseline_efficiency = None
        efficiency_delta = None
        efficiency_delta_percent = None

        if baseline_features is not None and baseline_features.efficiency_kwh_per_100km is not None:
            baseline_efficiency = baseline_features.efficiency_kwh_per_100km

            if features.efficiency_kwh_per_100km is not None:
                efficiency_delta = features.efficiency_kwh_per_100km - baseline_efficiency
                if abs(baseline_efficiency) > self.config.epsilon:
                    efficiency_delta_percent = (efficiency_delta / baseline_efficiency) * 100

        # Determine rating
        rating, rating_reason = self._determine_rating(
            features.efficiency_kwh_per_100km,
            baseline_efficiency,
            efficiency_delta_percent,
        )

        return EnergyAnalysisResult(
            energy_consumed_kwh=round(features.energy_consumed_kwh, self.config.energy_precision),
            energy_regenerated_kwh=round(features.energy_regenerated_kwh, self.config.energy_precision),
            net_energy_kwh=round(features.net_energy_kwh, self.config.energy_precision),
            distance_km=round(features.distance_km, self.config.distance_precision),
            energy_per_km=self._round_optional(features.energy_per_km, self.config.energy_precision),
            efficiency_kwh_per_100km=self._round_optional(
                features.efficiency_kwh_per_100km, self.config.energy_precision
            ),
            regen_ratio=self._round_optional(features.regen_ratio, self.config.percentage_precision),
            baseline_efficiency_kwh_per_100km=self._round_optional(
                baseline_efficiency, self.config.energy_precision
            ),
            efficiency_delta_kwh_per_100km=self._round_optional(
                efficiency_delta, self.config.energy_precision
            ),
            efficiency_delta_percent=self._round_optional(
                efficiency_delta_percent, self.config.percentage_precision
            ),
            rating=rating,
            rating_reason=rating_reason,
            duration_seconds=features.duration_seconds,
            sample_count=features.sample_count,
        )

    def _determine_rating(
        self,
        observed_efficiency: Optional[float],
        baseline_efficiency: Optional[float],
        delta_percent: Optional[float],
    ) -> tuple[EfficiencyRating, str]:
        """Determine efficiency rating based on comparison.

        Args:
            observed_efficiency: Observed kWh/100km
            baseline_efficiency: Baseline kWh/100km
            delta_percent: Percentage difference from baseline

        Returns:
            Tuple of (rating, reason)
        """
        if observed_efficiency is None:
            return (
                EfficiencyRating.UNKNOWN,
                "Cannot calculate efficiency - insufficient distance",
            )

        if baseline_efficiency is None or delta_percent is None:
            return (
                EfficiencyRating.UNKNOWN,
                "Baseline unavailable for comparison",
            )

        # Compare against baseline
        if delta_percent < self.EFFICIENT_THRESHOLD_PERCENT:
            return (
                EfficiencyRating.EFFICIENT,
                f"Efficiency is {abs(delta_percent):.1f}% better than baseline",
            )
        elif delta_percent > self.INEFFICIENT_THRESHOLD_PERCENT:
            return (
                EfficiencyRating.INEFFICIENT,
                f"Efficiency is {delta_percent:.1f}% worse than baseline",
            )
        else:
            return (
                EfficiencyRating.NORMAL,
                "Efficiency is within normal range of baseline",
            )

    def _round_optional(self, value: Optional[float], precision: int) -> Optional[float]:
        """Round a value if not None."""
        if value is None:
            return None
        return round(value, precision)
