"""Range estimation service.

This module provides estimated driving range calculations based on
current SOC and recent driving efficiency.

IMPORTANT: This is a PROTOTYPE intelligence estimate, not an
OEM-certified range prediction.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional

from app.intelligence.config import IntelligenceConfig, DEFAULT_CONFIG
from app.intelligence.features import TelemetryFeatures


class ConfidenceLevel(str, Enum):
    """Confidence level of intelligence analysis."""

    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


@dataclass
class RangeEstimationResult:
    """Result of range estimation."""

    # Current state
    current_soc_percent: float
    remaining_energy_kwh: float

    # Efficiency used for estimation
    efficiency_kwh_per_km: Optional[float]
    efficiency_source: str  # "observed", "baseline", or "unavailable"

    # Range estimate
    estimated_range_km: Optional[float]

    # Confidence
    confidence: ConfidenceLevel
    confidence_reason: str

    # Metadata
    disclaimer: str = (
        "This is a prototype intelligence estimate based on recent driving data. "
        "Actual range depends on driving conditions, terrain, climate, and vehicle state."
    )


class RangeEstimator:
    """Estimates remaining driving range.

    Formula:
        estimated_range_km = remaining_usable_energy_kwh / efficiency_kwh_per_km

    Where:
        remaining_usable_energy_kwh = usable_battery_capacity_kwh * (current_soc / 100)
        efficiency_kwh_per_km = recent driving efficiency

    IMPORTANT:
    - Charging-only simulations do NOT provide valid driving efficiency
    - If efficiency cannot be calculated, estimated_range_km is null
    - Uses usable battery capacity (57 kWh), not total capacity (60 kWh)
    """

    def __init__(self, config: IntelligenceConfig = DEFAULT_CONFIG):
        """Initialize range estimator.

        Args:
            config: Intelligence configuration
        """
        self.config = config

    def estimate(
        self,
        current_soc_percent: float,
        observed_features: Optional[TelemetryFeatures] = None,
        baseline_features: Optional[TelemetryFeatures] = None,
    ) -> RangeEstimationResult:
        """Estimate remaining driving range.

        Args:
            current_soc_percent: Current battery SOC (0-100)
            observed_features: Features from recent driving (for efficiency)
            baseline_features: Features from baseline driving (fallback efficiency)

        Returns:
            RangeEstimationResult with range estimate
        """
        # Calculate remaining energy
        remaining_energy = (
            self.config.usable_battery_capacity_kwh * (current_soc_percent / 100)
        )

        # Try to get efficiency from observed driving
        efficiency_kwh_per_km = None
        efficiency_source = "unavailable"

        if observed_features is not None and observed_features.energy_per_km is not None:
            # Observed features has valid driving efficiency
            if not observed_features.is_charging_session:
                efficiency_kwh_per_km = observed_features.energy_per_km
                efficiency_source = "observed"

        # Fallback to baseline if observed not available
        if efficiency_kwh_per_km is None and baseline_features is not None:
            if baseline_features.energy_per_km is not None:
                if not baseline_features.is_charging_session:
                    efficiency_kwh_per_km = baseline_features.energy_per_km
                    efficiency_source = "baseline"

        # Calculate range if efficiency available
        estimated_range = None
        if efficiency_kwh_per_km is not None and efficiency_kwh_per_km > self.config.epsilon:
            estimated_range = remaining_energy / efficiency_kwh_per_km

        # Determine confidence
        confidence, confidence_reason = self._determine_confidence(
            observed_features,
            baseline_features,
            efficiency_kwh_per_km,
            efficiency_source,
        )

        return RangeEstimationResult(
            current_soc_percent=round(current_soc_percent, self.config.percentage_precision),
            remaining_energy_kwh=round(remaining_energy, self.config.energy_precision),
            efficiency_kwh_per_km=self._round_optional(
                efficiency_kwh_per_km, self.config.energy_precision
            ),
            efficiency_source=efficiency_source,
            estimated_range_km=self._round_optional(
                estimated_range, self.config.distance_precision
            ),
            confidence=confidence,
            confidence_reason=confidence_reason,
        )

    def _determine_confidence(
        self,
        observed_features: Optional[TelemetryFeatures],
        baseline_features: Optional[TelemetryFeatures],
        efficiency: Optional[float],
        efficiency_source: str,
    ) -> tuple[ConfidenceLevel, str]:
        """Determine confidence level of range estimate.

        Returns:
            Tuple of (confidence level, reason)
        """
        if efficiency is None:
            return (
                ConfidenceLevel.LOW,
                "Cannot estimate range - no valid driving efficiency available",
            )

        # Check observed features quality
        if observed_features is not None and efficiency_source == "observed":
            # High confidence: good observed data
            if (
                observed_features.distance_km >= self.config.min_distance_for_high_confidence_km
                and observed_features.sample_count >= self.config.min_telemetry_samples_for_high_confidence
            ):
                return (
                    ConfidenceLevel.HIGH,
                    "Range estimate based on sufficient recent driving data",
                )
            elif observed_features.sample_count >= self.config.min_telemetry_samples_for_medium_confidence:
                return (
                    ConfidenceLevel.MEDIUM,
                    "Range estimate based on limited recent driving data",
                )
            else:
                return (
                    ConfidenceLevel.LOW,
                    "Range estimate based on minimal recent driving data",
                )

        # Using baseline efficiency
        if efficiency_source == "baseline":
            if baseline_features is not None:
                if (
                    baseline_features.distance_km >= self.config.min_distance_for_high_confidence_km
                    and baseline_features.sample_count >= self.config.min_telemetry_samples_for_high_confidence
                ):
                    return (
                        ConfidenceLevel.MEDIUM,
                        "Range estimate based on baseline driving data (not recent driving)",
                    )
            return (
                ConfidenceLevel.LOW,
                "Range estimate based on approximate baseline data",
            )

        return (
            ConfidenceLevel.LOW,
            "Range estimate has limited confidence due to data quality",
        )

    def _round_optional(self, value: Optional[float], precision: int) -> Optional[float]:
        """Round a value if not None."""
        if value is None:
            return None
        return round(value, precision)
