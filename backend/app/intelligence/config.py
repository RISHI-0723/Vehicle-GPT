"""Intelligence engine configuration and constants.

This module centralizes all configurable thresholds and parameters
for the Sprint 2 intelligence engine. Defaults are designed for
the VehicleGPT demo vehicle (VG-DEMO-001).

IMPORTANT: This is a PROTOTYPE intelligence system. Values here
are demonstration defaults, not scientifically validated thresholds.
"""

from dataclasses import dataclass, field
from typing import Dict


@dataclass(frozen=True)
class IntelligenceConfig:
    """Configuration for intelligence calculations.

    All thresholds and parameters are centralized here to:
    1. Avoid magic numbers throughout the codebase
    2. Enable easy configuration changes
    3. Support future per-vehicle customization
    """

    # === Battery Specifications ===
    usable_battery_capacity_kwh: float = 57.0
    total_battery_capacity_kwh: float = 60.0
    nominal_voltage: float = 400.0

    # === Numeric Stability ===
    epsilon: float = 1e-9  # Small value to prevent division by zero

    # === Temperature Thresholds ===
    # Prototype threshold for elevated battery temperature
    # Real LFP batteries tolerate higher temps, but this is for demonstration
    high_temperature_threshold_c: float = 40.0
    critical_temperature_threshold_c: float = 50.0
    optimal_temperature_min_c: float = 15.0
    optimal_temperature_max_c: float = 35.0

    # === Power Thresholds ===
    high_power_threshold_kw: float = 80.0  # High power draw threshold
    critical_power_threshold_kw: float = 120.0

    # === C-Rate Thresholds ===
    # C-rate = Power / Capacity, indicates charge/discharge intensity
    high_c_rate_threshold: float = 1.0  # 1C = full charge/discharge in 1 hour
    critical_c_rate_threshold: float = 2.0  # 2C = aggressive

    # === SOC Thresholds ===
    low_soc_threshold_percent: float = 20.0
    high_soc_threshold_percent: float = 90.0
    deep_discharge_threshold_percent: float = 10.0

    # === Speed Thresholds ===
    high_speed_threshold_kmh: float = 100.0

    # === Acceleration Thresholds ===
    high_acceleration_threshold_mps2: float = 2.5

    # === Anomaly Detection Weights (must sum to 1.0) ===
    anomaly_weight_energy: float = 0.60
    anomaly_weight_speed: float = 0.20
    anomaly_weight_acceleration: float = 0.10
    anomaly_weight_temperature: float = 0.10

    # === Anomaly Severity Thresholds ===
    anomaly_threshold_low: float = 25.0
    anomaly_threshold_medium: float = 50.0
    anomaly_threshold_high: float = 75.0
    anomaly_threshold_critical: float = 90.0

    # === Battery Stress Weights (must sum to 1.0) ===
    stress_weight_temperature: float = 0.30
    stress_weight_soc: float = 0.20
    stress_weight_power: float = 0.20
    stress_weight_driving: float = 0.15
    stress_weight_charging: float = 0.15

    # === Cost Calculation Defaults ===
    # Default battery replacement cost per kWh in INR
    # Based on approximate 2026 LFP costs in India
    default_battery_replacement_cost_per_kwh_inr: float = 10000.0

    # Wear cost fraction - small factor for estimating incremental wear
    # This is a PROTOTYPE proxy, not a real degradation model
    default_wear_cost_fraction: float = 0.0001

    # === Contributor Impact Thresholds ===
    contributor_impact_low_max: float = 0.24
    contributor_impact_medium_max: float = 0.49
    contributor_impact_high_max: float = 0.74
    # Above 0.74 is CRITICAL

    # === Confidence Thresholds ===
    min_distance_for_high_confidence_km: float = 5.0
    min_telemetry_samples_for_high_confidence: int = 10
    min_telemetry_samples_for_medium_confidence: int = 3

    # === Recommendation Limits ===
    max_recommendations: int = 5

    # === Rounding Precision ===
    energy_precision: int = 3
    distance_precision: int = 2
    percentage_precision: int = 2
    score_precision: int = 2

    def validate(self) -> None:
        """Validate configuration consistency."""
        # Anomaly weights must sum to 1.0
        anomaly_sum = (
            self.anomaly_weight_energy +
            self.anomaly_weight_speed +
            self.anomaly_weight_acceleration +
            self.anomaly_weight_temperature
        )
        assert abs(anomaly_sum - 1.0) < 0.001, f"Anomaly weights sum to {anomaly_sum}, not 1.0"

        # Stress weights must sum to 1.0
        stress_sum = (
            self.stress_weight_temperature +
            self.stress_weight_soc +
            self.stress_weight_power +
            self.stress_weight_driving +
            self.stress_weight_charging
        )
        assert abs(stress_sum - 1.0) < 0.001, f"Stress weights sum to {stress_sum}, not 1.0"


# Default configuration instance
DEFAULT_CONFIG = IntelligenceConfig()

# Validate on import
DEFAULT_CONFIG.validate()
