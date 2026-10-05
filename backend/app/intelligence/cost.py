"""Cost-of-driving analysis service.

This module calculates operating costs including energy cost
and a prototype battery wear proxy.

IMPORTANT: The battery wear cost is a PROTOTYPE economic proxy,
NOT a real battery degradation model.
"""

from dataclasses import dataclass
from typing import Optional

from app.intelligence.config import IntelligenceConfig, DEFAULT_CONFIG
from app.intelligence.features import TelemetryFeatures


@dataclass
class CostAnalysisResult:
    """Result of cost analysis.

    DISCLAIMER: Battery wear cost is a prototype proxy based on
    operational factors. It is NOT a warranty assessment or
    degradation prediction.
    """

    # Energy cost
    energy_cost_inr: float
    electricity_price_per_kwh: float
    energy_used_kwh: float

    # Wear proxy
    wear_factor: float  # 0-1
    estimated_battery_wear_cost_inr: float

    # Total
    total_operating_cost_inr: float

    # Cost breakdown
    cost_per_km_inr: Optional[float]

    # Metadata
    distance_km: float
    duration_seconds: float

    # Disclaimer
    disclaimer: str = (
        "Battery wear cost is a prototype economic proxy based on operational factors "
        "(energy throughput, temperature stress, power demand). It is NOT a battery "
        "degradation prediction, warranty assessment, or remaining life estimate."
    )


class CostAnalyzer:
    """Analyzes operating costs for driving sessions.

    COST CALCULATION:
        energy_cost = energy_consumed * electricity_price_per_kwh

    BATTERY WEAR PROXY (PROTOTYPE):
        normalized_energy_throughput: energy used / usable capacity
        normalized_battery_stress: from stress analysis (0-1)
        normalized_high_temp_exposure: fraction of time at high temp

        wear_factor = clamp(
            0.50 * normalized_energy_throughput +
            0.30 * normalized_battery_stress +
            0.20 * normalized_high_temp_exposure,
            0, 1
        )

        estimated_battery_wear_cost = (
            wear_factor *
            wear_cost_fraction *
            battery_replacement_cost_per_kwh *
            usable_capacity
        )

    Note: This uses NET energy (consumed - regen) for cost calculation.
    """

    def __init__(self, config: IntelligenceConfig = DEFAULT_CONFIG):
        """Initialize cost analyzer.

        Args:
            config: Intelligence configuration
        """
        self.config = config

    def analyze(
        self,
        features: TelemetryFeatures,
        electricity_price_per_kwh: float,
        battery_stress_score: float = 0.0,
        battery_replacement_cost_per_kwh_inr: Optional[float] = None,
        wear_cost_fraction: Optional[float] = None,
    ) -> CostAnalysisResult:
        """Analyze operating costs.

        Args:
            features: Extracted telemetry features
            electricity_price_per_kwh: Electricity price in INR
            battery_stress_score: Battery stress score (0-100)
            battery_replacement_cost_per_kwh_inr: Battery replacement cost (optional)
            wear_cost_fraction: Wear cost fraction (optional)

        Returns:
            CostAnalysisResult with costs

        Raises:
            ValueError: If electricity_price_per_kwh <= 0
        """
        if electricity_price_per_kwh <= 0:
            raise ValueError("electricity_price_per_kwh must be positive")

        # Use defaults if not provided
        battery_cost = (
            battery_replacement_cost_per_kwh_inr
            or self.config.default_battery_replacement_cost_per_kwh_inr
        )
        wear_fraction = (
            wear_cost_fraction or self.config.default_wear_cost_fraction
        )

        # Calculate energy cost using net energy
        energy_used = features.net_energy_kwh
        energy_cost = energy_used * electricity_price_per_kwh

        # Calculate wear factor
        wear_factor = self._calculate_wear_factor(
            features, battery_stress_score
        )

        # Calculate estimated battery wear cost
        battery_wear_cost = (
            wear_factor *
            wear_fraction *
            battery_cost *
            self.config.usable_battery_capacity_kwh
        )

        # Total operating cost
        total_cost = energy_cost + battery_wear_cost

        # Cost per km
        cost_per_km = None
        if features.distance_km > self.config.epsilon:
            cost_per_km = total_cost / features.distance_km

        return CostAnalysisResult(
            energy_cost_inr=round(energy_cost, 2),
            electricity_price_per_kwh=electricity_price_per_kwh,
            energy_used_kwh=round(energy_used, self.config.energy_precision),
            wear_factor=round(wear_factor, 4),
            estimated_battery_wear_cost_inr=round(battery_wear_cost, 2),
            total_operating_cost_inr=round(total_cost, 2),
            cost_per_km_inr=self._round_optional(cost_per_km, 2),
            distance_km=round(features.distance_km, self.config.distance_precision),
            duration_seconds=features.duration_seconds,
        )

    def _calculate_wear_factor(
        self,
        features: TelemetryFeatures,
        battery_stress_score: float,
    ) -> float:
        """Calculate battery wear factor (0-1).

        Formula:
            wear_factor = clamp(
                0.50 * normalized_energy_throughput +
                0.30 * normalized_battery_stress +
                0.20 * normalized_high_temp_exposure,
                0, 1
            )

        Args:
            features: Telemetry features
            battery_stress_score: Battery stress score (0-100)

        Returns:
            Wear factor between 0 and 1
        """
        # Normalized energy throughput (cycles equivalent)
        # 1.0 = one full cycle (57 kWh throughput)
        energy_throughput = abs(features.net_energy_kwh)
        normalized_throughput = min(
            energy_throughput / self.config.usable_battery_capacity_kwh,
            1.0
        )

        # Normalized battery stress (0-100 -> 0-1)
        normalized_stress = min(battery_stress_score / 100.0, 1.0)

        # High temperature exposure ratio (already 0-1)
        normalized_temp_exposure = features.high_temperature_exposure_ratio

        # Calculate weighted wear factor
        wear_factor = (
            0.50 * normalized_throughput +
            0.30 * normalized_stress +
            0.20 * normalized_temp_exposure
        )

        return max(0.0, min(1.0, wear_factor))

    def _round_optional(self, value: Optional[float], precision: int) -> Optional[float]:
        """Round a value if not None."""
        if value is None:
            return None
        return round(value, precision)
