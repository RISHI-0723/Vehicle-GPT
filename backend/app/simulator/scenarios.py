"""Simulation scenario configurations.

Each scenario defines parameters that influence telemetry generation.
Scenarios affect actual telemetry values, not just summary numbers.
"""
from dataclasses import dataclass, field
from typing import Optional
from enum import Enum


class ScenarioType(str, Enum):
    """Scenario type identifiers."""
    NORMAL_DRIVING = "NORMAL_DRIVING"
    HOT_INDIAN_DAY = "HOT_INDIAN_DAY"
    AGGRESSIVE_DRIVING = "AGGRESSIVE_DRIVING"
    FAST_CHARGING = "FAST_CHARGING"
    ENERGY_ANOMALY = "ENERGY_ANOMALY"


@dataclass
class ScenarioConfig:
    """Configuration for a simulation scenario.

    These parameters influence the simulation engine's behavior
    to produce scenario-specific telemetry.
    """

    name: str
    description: str

    # Temperature settings
    ambient_temp_min_c: float = 20.0
    ambient_temp_max_c: float = 28.0
    ambient_temp_variation: float = 2.0  # Random variation range

    # Speed settings (km/h)
    target_speed_min: float = 30.0
    target_speed_max: float = 80.0
    speed_variation: float = 10.0

    # Acceleration settings (m/s^2)
    acceleration_magnitude: float = 1.5
    acceleration_variation: float = 0.5
    harsh_accel_threshold: float = 3.0
    harsh_brake_threshold: float = -3.0

    # Driving behavior
    harsh_event_probability: float = 0.02  # Per sample
    aggressive_base_score: float = 10.0
    aggressive_score_variation: float = 5.0

    # Terrain
    gradient_mean: float = 0.0
    gradient_variation: float = 1.0

    # Charging (only for FAST_CHARGING scenario)
    is_charging: bool = False
    charging_power_kw: float = 0.0
    charger_id: Optional[str] = None

    # Energy anomaly settings (only for ENERGY_ANOMALY scenario)
    has_anomaly: bool = False
    anomaly_start_fraction: float = 0.5  # Start anomaly at 50% through simulation
    anomaly_duration_fraction: float = 0.3  # Anomaly lasts 30% of simulation
    anomaly_consumption_multiplier: float = 1.25  # 25% increase minimum

    # Efficiency modifiers
    base_efficiency_multiplier: float = 1.0
    hvac_load_multiplier: float = 1.0


# Scenario descriptions for API response
SCENARIO_DESCRIPTIONS = {
    ScenarioType.NORMAL_DRIVING: "Moderate temperature and smooth everyday driving.",
    ScenarioType.HOT_INDIAN_DAY: "Hot ambient conditions with increased thermal and auxiliary load.",
    ScenarioType.AGGRESSIVE_DRIVING: "Frequent acceleration and harsh braking.",
    ScenarioType.FAST_CHARGING: "Stationary high-power charging with rising SOC.",
    ScenarioType.ENERGY_ANOMALY: "Normal driving followed by a controlled energy-consumption anomaly.",
}


def get_scenario_config(scenario: str) -> ScenarioConfig:
    """Get configuration for a specific scenario.

    Args:
        scenario: Scenario name string

    Returns:
        ScenarioConfig for the requested scenario

    Raises:
        ValueError: If scenario is not recognized
    """
    scenario_upper = scenario.upper()

    if scenario_upper == ScenarioType.NORMAL_DRIVING:
        return ScenarioConfig(
            name="NORMAL_DRIVING",
            description=SCENARIO_DESCRIPTIONS[ScenarioType.NORMAL_DRIVING],
            ambient_temp_min_c=22.0,
            ambient_temp_max_c=28.0,
            ambient_temp_variation=2.0,
            target_speed_min=40.0,
            target_speed_max=70.0,
            speed_variation=8.0,
            acceleration_magnitude=1.2,
            acceleration_variation=0.4,
            harsh_event_probability=0.01,
            aggressive_base_score=8.0,
            aggressive_score_variation=4.0,
            gradient_mean=0.0,
            gradient_variation=0.5,
            base_efficiency_multiplier=1.0,
            hvac_load_multiplier=1.0,
        )

    elif scenario_upper == ScenarioType.HOT_INDIAN_DAY:
        return ScenarioConfig(
            name="HOT_INDIAN_DAY",
            description=SCENARIO_DESCRIPTIONS[ScenarioType.HOT_INDIAN_DAY],
            # Realistic hot Indian temperatures (35-45C in summer)
            ambient_temp_min_c=38.0,
            ambient_temp_max_c=44.0,
            ambient_temp_variation=2.0,
            target_speed_min=35.0,
            target_speed_max=65.0,
            speed_variation=10.0,
            acceleration_magnitude=1.3,
            acceleration_variation=0.5,
            harsh_event_probability=0.015,
            aggressive_base_score=12.0,
            aggressive_score_variation=5.0,
            gradient_mean=0.0,
            gradient_variation=0.5,
            # Higher HVAC load due to cooling demand
            base_efficiency_multiplier=1.15,
            hvac_load_multiplier=1.8,
        )

    elif scenario_upper == ScenarioType.AGGRESSIVE_DRIVING:
        return ScenarioConfig(
            name="AGGRESSIVE_DRIVING",
            description=SCENARIO_DESCRIPTIONS[ScenarioType.AGGRESSIVE_DRIVING],
            ambient_temp_min_c=24.0,
            ambient_temp_max_c=30.0,
            ambient_temp_variation=2.0,
            target_speed_min=50.0,
            target_speed_max=100.0,
            speed_variation=15.0,
            # Higher acceleration magnitudes
            acceleration_magnitude=2.5,
            acceleration_variation=1.0,
            harsh_accel_threshold=2.5,
            harsh_brake_threshold=-2.5,
            # Much higher harsh event probability
            harsh_event_probability=0.15,
            aggressive_base_score=45.0,
            aggressive_score_variation=15.0,
            gradient_mean=0.0,
            gradient_variation=1.0,
            # Higher consumption from aggressive driving
            base_efficiency_multiplier=1.3,
            hvac_load_multiplier=1.0,
        )

    elif scenario_upper == ScenarioType.FAST_CHARGING:
        return ScenarioConfig(
            name="FAST_CHARGING",
            description=SCENARIO_DESCRIPTIONS[ScenarioType.FAST_CHARGING],
            ambient_temp_min_c=25.0,
            ambient_temp_max_c=30.0,
            ambient_temp_variation=1.0,
            # Vehicle is stationary
            target_speed_min=0.0,
            target_speed_max=0.0,
            speed_variation=0.0,
            acceleration_magnitude=0.0,
            acceleration_variation=0.0,
            harsh_event_probability=0.0,
            aggressive_base_score=0.0,
            aggressive_score_variation=0.0,
            gradient_mean=0.0,
            gradient_variation=0.0,
            # Charging settings
            is_charging=True,
            charging_power_kw=120.0,  # 120kW DC fast charging
            charger_id="DC-FAST-001",
            base_efficiency_multiplier=1.0,
            hvac_load_multiplier=0.5,  # Lower HVAC while stationary
        )

    elif scenario_upper == ScenarioType.ENERGY_ANOMALY:
        return ScenarioConfig(
            name="ENERGY_ANOMALY",
            description=SCENARIO_DESCRIPTIONS[ScenarioType.ENERGY_ANOMALY],
            ambient_temp_min_c=24.0,
            ambient_temp_max_c=28.0,
            ambient_temp_variation=1.5,
            target_speed_min=45.0,
            target_speed_max=65.0,
            speed_variation=5.0,  # Tighter speed control for comparison
            acceleration_magnitude=1.2,
            acceleration_variation=0.3,  # Less variation for comparison
            harsh_event_probability=0.01,
            aggressive_base_score=10.0,
            aggressive_score_variation=3.0,
            gradient_mean=0.0,
            gradient_variation=0.3,
            # Anomaly configuration
            has_anomaly=True,
            anomaly_start_fraction=0.4,  # Start at 40% through
            anomaly_duration_fraction=0.35,  # Last 35% of simulation
            anomaly_consumption_multiplier=1.25,  # At least 25% increase
            base_efficiency_multiplier=1.0,
            hvac_load_multiplier=1.0,
        )

    else:
        raise ValueError(f"Unknown scenario: {scenario}")
