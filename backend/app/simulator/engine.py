"""Deterministic EV telemetry simulation engine.

This engine generates synthetic telemetry data for EV simulation.
All randomness uses a local RNG seeded for determinism.
Given identical inputs, output is identical.

IMPORTANT: This is SYNTHETIC SIMULATED DATA, not real vehicle telemetry.
"""
import logging
import random
import uuid
from dataclasses import dataclass, field, replace
from datetime import datetime, timedelta, timezone
from typing import List, Optional, Dict, Any

from app.core.config import DEFAULT_SIMULATION_START_TIME
from app.simulator.physics import EVPhysics
from app.simulator.scenarios import ScenarioConfig, get_scenario_config

logger = logging.getLogger(__name__)


@dataclass
class TelemetryPoint:
    """A single telemetry data point."""

    simulation_id: str
    vehicle_id: str
    timestamp: datetime

    # Battery
    soc_percent: float
    soh_percent: float
    battery_temperature_c: float
    pack_voltage_v: float
    pack_current_a: float
    battery_power_kw: float

    # Vehicle
    speed_kmh: float
    acceleration_mps2: float
    odometer_km: float
    trip_distance_km: float

    # Energy
    energy_consumed_kwh: float
    energy_consumption_kwh_per_100km: float
    regenerative_energy_kwh: float

    # Environment
    ambient_temperature_c: float
    elevation_m: float
    road_gradient_percent: float

    # Driving
    harsh_acceleration: bool
    harsh_braking: bool
    aggressive_driving_score: float

    # Charging
    charging: bool
    charging_power_kw: float
    charger_id: Optional[str]


@dataclass
class SimulationResult:
    """Complete simulation result with telemetry and summary."""

    simulation_id: str
    vehicle_id: str
    scenario: str
    mode: str
    seed: int
    start_time: datetime
    duration_minutes: int
    interval_seconds: int
    samples_generated: int
    telemetry: List[TelemetryPoint]

    # Summary metrics
    starting_soc: float
    ending_soc: float
    starting_odometer: float
    ending_odometer: float
    energy_consumed: float
    distance: float
    average_efficiency: float
    max_battery_temperature: float
    peak_power: float

    # ENERGY_ANOMALY specific
    anomaly_started_at: Optional[datetime] = None
    anomaly_ended_at: Optional[datetime] = None
    baseline_consumption: Optional[float] = None
    anomaly_consumption: Optional[float] = None
    anomaly_increase_percent: Optional[float] = None


@dataclass
class VehicleState:
    """Current state of the simulated vehicle."""

    soc_percent: float
    soh_percent: float
    battery_temperature_c: float
    odometer_km: float
    speed_kmh: float = 0.0
    trip_distance_km: float = 0.0
    energy_consumed_kwh: float = 0.0
    regenerative_energy_kwh: float = 0.0
    elevation_m: float = 0.0

    @classmethod
    def from_baseline(cls, vehicle_config: Dict[str, Any]) -> "VehicleState":
        """Canonical fresh-mode starting state (state BEFORE the first simulation step)."""
        return cls(
            soc_percent=vehicle_config["initial_soc_percent"],
            soh_percent=vehicle_config["initial_soh_percent"],
            battery_temperature_c=vehicle_config["initial_battery_temperature_c"],
            odometer_km=vehicle_config["initial_odometer_km"],
        )

    @classmethod
    def from_telemetry(cls, row: Any) -> "VehicleState":
        """Full state recorded by a telemetry row (used as continue-mode starting state).

        Accepts any object exposing the telemetry state attributes, such as a
        persisted Telemetry row. Each row holds the state AFTER its own step.
        """
        return cls(
            soc_percent=row.soc_percent,
            soh_percent=row.soh_percent,
            battery_temperature_c=row.battery_temperature_c,
            odometer_km=row.odometer_km,
            speed_kmh=row.speed_kmh,
            trip_distance_km=row.trip_distance_km,
            energy_consumed_kwh=row.energy_consumed_kwh,
            regenerative_energy_kwh=row.regenerative_energy_kwh,
            elevation_m=row.elevation_m,
        )


class SimulationEngine:
    """Deterministic EV telemetry simulation engine.

    Uses local RNG for determinism. Given identical:
    - vehicle baseline
    - scenario
    - duration
    - interval
    - seed
    - mode
    - starting state
    - simulation_start_time

    The generated telemetry is identical.
    """

    def __init__(
        self,
        vehicle_config: Dict[str, Any],
        scenario: str,
        duration_minutes: int,
        interval_seconds: int,
        seed: int,
        mode: str,
        simulation_start_time: Optional[datetime] = None,
        previous_state: Optional[VehicleState] = None,
        previous_timestamp: Optional[datetime] = None,
        initial_state: Optional[VehicleState] = None,
    ):
        """Initialize simulation engine.

        Args:
            vehicle_config: Vehicle configuration dict
            scenario: Scenario name
            duration_minutes: Simulation duration
            interval_seconds: Time between samples
            seed: Random seed for determinism
            mode: 'fresh' or 'continue'
            simulation_start_time: Custom start time (fresh mode only)
            previous_state: Previous vehicle state (continue mode)
            previous_timestamp: Previous latest timestamp (continue mode)
            initial_state: Explicit starting state (fresh mode only). When omitted,
                the canonical baseline from vehicle_config is used.
        """
        self.vehicle_id = vehicle_config["vehicle_id"]
        self.scenario_name = scenario
        self.scenario_config = get_scenario_config(scenario)
        self.duration_minutes = duration_minutes
        self.interval_seconds = interval_seconds
        self.seed = seed
        self.mode = mode

        # Initialize LOCAL random number generator for determinism
        self.rng = random.Random(seed)

        # Generate simulation ID deterministically
        self.simulation_id = self._generate_simulation_id()

        # Initialize physics engine
        self.physics = EVPhysics(
            battery_capacity_kwh=vehicle_config["battery_capacity_kwh"],
            usable_capacity_kwh=vehicle_config["usable_battery_capacity_kwh"],
        )

        # Determine starting state
        if mode == "continue" and previous_state is not None:
            self.state = previous_state
            # In continue mode, ignore simulation_start_time
            if previous_timestamp is not None:
                self.current_time = previous_timestamp + timedelta(seconds=interval_seconds)
            else:
                self.current_time = DEFAULT_SIMULATION_START_TIME
        else:
            # Fresh mode - canonical baseline unless an explicit starting state is supplied
            if initial_state is not None:
                # Copy so the engine's in-place stepping never mutates the caller's state
                self.state = replace(initial_state)
            else:
                self.state = VehicleState.from_baseline(vehicle_config)
            if simulation_start_time is not None:
                self.current_time = simulation_start_time
            else:
                self.current_time = DEFAULT_SIMULATION_START_TIME

        # Ensure timezone-aware
        if self.current_time.tzinfo is None:
            self.current_time = self.current_time.replace(tzinfo=timezone.utc)

        # Store initial values for summary
        self.starting_soc = self.state.soc_percent
        self.starting_odometer = self.state.odometer_km

        # Calculate number of samples
        total_seconds = duration_minutes * 60
        self.num_samples = total_seconds // interval_seconds

        logger.info(
            f"Simulation engine initialized: {self.simulation_id}, "
            f"scenario={scenario}, samples={self.num_samples}, seed={seed}"
        )

    def _generate_simulation_id(self) -> str:
        """Generate unique simulation ID.

        Uses UUID for uniqueness. Each simulation gets a unique ID even with
        the same seed, which is necessary to avoid database conflicts.
        The determinism guarantee is about telemetry content, not simulation IDs.
        """
        return f"sim-{uuid.uuid4().hex[:12]}"

    def run(self) -> SimulationResult:
        """Run the simulation and generate telemetry.

        Returns:
            SimulationResult with telemetry and summary
        """
        logger.info(f"Starting simulation {self.simulation_id}")

        telemetry: List[TelemetryPoint] = []
        max_battery_temp = self.state.battery_temperature_c
        peak_power = 0.0

        # For ENERGY_ANOMALY scenario tracking
        anomaly_start_idx = None
        anomaly_end_idx = None
        baseline_consumptions = []
        anomaly_consumptions = []

        if self.scenario_config.has_anomaly:
            anomaly_start_idx = int(self.num_samples * self.scenario_config.anomaly_start_fraction)
            anomaly_end_idx = int(
                self.num_samples * (
                    self.scenario_config.anomaly_start_fraction +
                    self.scenario_config.anomaly_duration_fraction
                )
            )

        # Generate telemetry points
        for i in range(self.num_samples):
            # Determine if we're in anomaly phase
            in_anomaly = (
                self.scenario_config.has_anomaly and
                anomaly_start_idx is not None and
                anomaly_end_idx is not None and
                anomaly_start_idx <= i < anomaly_end_idx
            )

            point = self._generate_point(i, in_anomaly)
            telemetry.append(point)

            # Track maximums
            max_battery_temp = max(max_battery_temp, point.battery_temperature_c)
            peak_power = max(peak_power, abs(point.battery_power_kw))

            # Track consumption for anomaly analysis
            if self.scenario_config.has_anomaly and point.speed_kmh > 0:
                if in_anomaly:
                    anomaly_consumptions.append(point.energy_consumption_kwh_per_100km)
                elif i < (anomaly_start_idx or 0):
                    baseline_consumptions.append(point.energy_consumption_kwh_per_100km)

            # Advance time
            self.current_time += timedelta(seconds=self.interval_seconds)

        # Calculate summary
        ending_soc = self.state.soc_percent
        ending_odometer = self.state.odometer_km
        total_distance = ending_odometer - self.starting_odometer
        energy_consumed = self.state.energy_consumed_kwh

        if total_distance > 0:
            avg_efficiency = (energy_consumed / total_distance) * 100
        else:
            avg_efficiency = 0.0

        # Anomaly analysis
        anomaly_started_at = None
        anomaly_ended_at = None
        baseline_consumption = None
        anomaly_consumption = None
        anomaly_increase_percent = None

        if self.scenario_config.has_anomaly and telemetry:
            if anomaly_start_idx is not None and anomaly_start_idx < len(telemetry):
                anomaly_started_at = telemetry[anomaly_start_idx].timestamp
            if anomaly_end_idx is not None and anomaly_end_idx <= len(telemetry):
                anomaly_ended_at = telemetry[min(anomaly_end_idx, len(telemetry) - 1)].timestamp

            if baseline_consumptions:
                baseline_consumption = sum(baseline_consumptions) / len(baseline_consumptions)
            if anomaly_consumptions:
                anomaly_consumption = sum(anomaly_consumptions) / len(anomaly_consumptions)

            if baseline_consumption and anomaly_consumption and baseline_consumption > 0:
                anomaly_increase_percent = (
                    (anomaly_consumption - baseline_consumption) / baseline_consumption
                ) * 100

        result = SimulationResult(
            simulation_id=self.simulation_id,
            vehicle_id=self.vehicle_id,
            scenario=self.scenario_name,
            mode=self.mode,
            seed=self.seed,
            start_time=telemetry[0].timestamp if telemetry else self.current_time,
            duration_minutes=self.duration_minutes,
            interval_seconds=self.interval_seconds,
            samples_generated=len(telemetry),
            telemetry=telemetry,
            starting_soc=self.starting_soc,
            ending_soc=ending_soc,
            starting_odometer=self.starting_odometer,
            ending_odometer=ending_odometer,
            energy_consumed=round(energy_consumed, 4),
            distance=round(total_distance, 4),
            average_efficiency=round(avg_efficiency, 2),
            max_battery_temperature=round(max_battery_temp, 2),
            peak_power=round(peak_power, 2),
            anomaly_started_at=anomaly_started_at,
            anomaly_ended_at=anomaly_ended_at,
            baseline_consumption=round(baseline_consumption, 2) if baseline_consumption else None,
            anomaly_consumption=round(anomaly_consumption, 2) if anomaly_consumption else None,
            anomaly_increase_percent=round(anomaly_increase_percent, 2) if anomaly_increase_percent else None,
        )

        logger.info(
            f"Simulation {self.simulation_id} complete: "
            f"{len(telemetry)} samples, SOC {self.starting_soc:.1f}% -> {ending_soc:.1f}%"
        )

        return result

    def _generate_point(self, index: int, in_anomaly: bool) -> TelemetryPoint:
        """Generate a single telemetry point.

        Args:
            index: Point index in simulation
            in_anomaly: Whether we're in anomaly phase

        Returns:
            TelemetryPoint with correlated values
        """
        cfg = self.scenario_config

        # Generate ambient temperature
        ambient_temp = self.rng.uniform(cfg.ambient_temp_min_c, cfg.ambient_temp_max_c)
        ambient_temp += self.rng.uniform(-cfg.ambient_temp_variation, cfg.ambient_temp_variation)

        # Generate road gradient
        gradient = cfg.gradient_mean + self.rng.uniform(-cfg.gradient_variation, cfg.gradient_variation)

        # Charging scenario
        if cfg.is_charging:
            return self._generate_charging_point(index, ambient_temp, gradient)

        # Driving scenario
        return self._generate_driving_point(index, ambient_temp, gradient, in_anomaly)

    def _generate_driving_point(
        self,
        index: int,
        ambient_temp: float,
        gradient: float,
        in_anomaly: bool,
    ) -> TelemetryPoint:
        """Generate a driving telemetry point with correlated values."""
        cfg = self.scenario_config

        # Generate target speed
        target_speed = self.rng.uniform(cfg.target_speed_min, cfg.target_speed_max)

        # Smooth speed changes
        speed_diff = target_speed - self.state.speed_kmh
        max_speed_change = cfg.acceleration_magnitude * 3.6 * self.interval_seconds
        speed_change = max(-max_speed_change, min(max_speed_change, speed_diff * 0.3))
        speed_change += self.rng.uniform(-cfg.speed_variation, cfg.speed_variation)

        new_speed = max(0, self.state.speed_kmh + speed_change)

        # Calculate acceleration
        acceleration = (new_speed - self.state.speed_kmh) / 3.6 / self.interval_seconds

        # Determine harsh events
        harsh_accel = abs(acceleration) > cfg.harsh_accel_threshold and acceleration > 0
        harsh_brake = acceleration < cfg.harsh_brake_threshold

        # Random harsh event injection
        if self.rng.random() < cfg.harsh_event_probability:
            if self.rng.random() < 0.5:
                harsh_accel = True
                acceleration = cfg.harsh_accel_threshold + self.rng.uniform(0.5, 1.5)
            else:
                harsh_brake = True
                acceleration = cfg.harsh_brake_threshold - self.rng.uniform(0.5, 1.5)

        # Aggressive driving score
        aggressive_score = cfg.aggressive_base_score
        aggressive_score += self.rng.uniform(-cfg.aggressive_score_variation, cfg.aggressive_score_variation)
        if harsh_accel:
            aggressive_score += 15
        if harsh_brake:
            aggressive_score += 10
        aggressive_score = max(0, min(100, aggressive_score))

        # Calculate power demand
        efficiency_mult = cfg.base_efficiency_multiplier
        if in_anomaly:
            # Apply anomaly multiplier
            efficiency_mult *= cfg.anomaly_consumption_multiplier

        battery_power, consumption_rate, hvac_load = self.physics.calculate_power_demand(
            speed_kmh=new_speed,
            acceleration_mps2=acceleration,
            gradient_percent=gradient,
            ambient_temp_c=ambient_temp,
            rng=self.rng,
        )

        # Apply efficiency multiplier
        battery_power *= efficiency_mult

        # Apply HVAC multiplier
        extra_hvac = hvac_load * (cfg.hvac_load_multiplier - 1.0)
        battery_power += extra_hvac

        # Recalculate consumption rate with modifications
        if new_speed > 0:
            consumption_rate = (battery_power / new_speed) * 100
        else:
            consumption_rate = 0.0

        # Calculate regeneration
        regen_power = 0.0
        if acceleration < 0 and new_speed > 5:
            regen_power = self.physics.calculate_regeneration(
                deceleration_mps2=acceleration,
                speed_kmh=new_speed,
                rng=self.rng,
            )
            # Regen reduces net battery power
            battery_power -= regen_power

        # Calculate voltage and current
        pack_voltage = self.physics.calculate_pack_voltage(self.state.soc_percent, self.rng)
        pack_current = self.physics.calculate_pack_current(battery_power, pack_voltage)

        # Calculate energy change
        interval_hours = self.interval_seconds / 3600
        energy_delta = battery_power * interval_hours
        self.state.energy_consumed_kwh += max(0, energy_delta)
        self.state.regenerative_energy_kwh += regen_power * interval_hours

        # Update SOC
        new_soc = self.physics.calculate_soc_change(
            self.state.soc_percent,
            -energy_delta,  # Negative because discharge consumes energy
        )

        # Update battery temperature
        new_battery_temp = self.physics.calculate_battery_temperature_change(
            current_temp_c=self.state.battery_temperature_c,
            ambient_temp_c=ambient_temp,
            power_kw=battery_power,
            charging=False,
            interval_seconds=self.interval_seconds,
            rng=self.rng,
        )

        # Update distance
        distance_delta = (new_speed / 3600) * self.interval_seconds
        self.state.trip_distance_km += distance_delta
        self.state.odometer_km += distance_delta

        # Update state
        self.state.speed_kmh = new_speed
        self.state.soc_percent = new_soc
        self.state.battery_temperature_c = new_battery_temp

        return TelemetryPoint(
            simulation_id=self.simulation_id,
            vehicle_id=self.vehicle_id,
            timestamp=self.current_time,
            soc_percent=round(new_soc, 2),
            soh_percent=round(self.state.soh_percent, 2),  # SOH constant in Sprint 1
            battery_temperature_c=round(new_battery_temp, 2),
            pack_voltage_v=round(pack_voltage, 2),
            pack_current_a=round(pack_current, 2),
            battery_power_kw=round(battery_power, 3),
            speed_kmh=round(new_speed, 2),
            acceleration_mps2=round(acceleration, 3),
            odometer_km=round(self.state.odometer_km, 3),
            trip_distance_km=round(self.state.trip_distance_km, 3),
            energy_consumed_kwh=round(self.state.energy_consumed_kwh, 4),
            energy_consumption_kwh_per_100km=round(max(0, consumption_rate), 2),
            regenerative_energy_kwh=round(self.state.regenerative_energy_kwh, 4),
            ambient_temperature_c=round(ambient_temp, 2),
            elevation_m=round(self.state.elevation_m, 2),
            road_gradient_percent=round(gradient, 2),
            harsh_acceleration=harsh_accel,
            harsh_braking=harsh_brake,
            aggressive_driving_score=round(aggressive_score, 2),
            charging=False,
            charging_power_kw=0.0,
            charger_id=None,
        )

    def _generate_charging_point(
        self,
        index: int,
        ambient_temp: float,
        gradient: float,
    ) -> TelemetryPoint:
        """Generate a charging telemetry point.

        Charging semantics:
        - speed = 0
        - charging = true
        - charging_power_kw > 0 (power INTO battery)
        - battery_power_kw < 0 (negative = charging)
        - pack_current_a < 0 (negative = charging)
        - SOC increases
        """
        cfg = self.scenario_config

        # Vehicle is stationary
        self.state.speed_kmh = 0.0

        # Calculate charging power based on SOC
        charging_power = self.physics.calculate_charging_power(
            soc_percent=self.state.soc_percent,
            max_power_kw=cfg.charging_power_kw,
            rng=self.rng,
        )

        # Battery power is negative during charging (energy INTO battery)
        battery_power = -charging_power * self.physics.charging_efficiency

        # Calculate voltage and current (current negative during charge)
        pack_voltage = self.physics.calculate_pack_voltage(self.state.soc_percent, self.rng)
        pack_current = self.physics.calculate_pack_current(battery_power, pack_voltage)

        # Calculate SOC increase
        interval_hours = self.interval_seconds / 3600
        energy_added = charging_power * self.physics.charging_efficiency * interval_hours

        new_soc = self.physics.calculate_soc_change(
            self.state.soc_percent,
            energy_added,  # Positive = charging
        )

        # Battery temperature rises during charging
        new_battery_temp = self.physics.calculate_battery_temperature_change(
            current_temp_c=self.state.battery_temperature_c,
            ambient_temp_c=ambient_temp,
            power_kw=charging_power,
            charging=True,
            interval_seconds=self.interval_seconds,
            rng=self.rng,
        )

        # Update state
        self.state.soc_percent = new_soc
        self.state.battery_temperature_c = new_battery_temp

        return TelemetryPoint(
            simulation_id=self.simulation_id,
            vehicle_id=self.vehicle_id,
            timestamp=self.current_time,
            soc_percent=round(new_soc, 2),
            soh_percent=round(self.state.soh_percent, 2),  # SOH constant
            battery_temperature_c=round(new_battery_temp, 2),
            pack_voltage_v=round(pack_voltage, 2),
            pack_current_a=round(pack_current, 2),  # Negative during charge
            battery_power_kw=round(battery_power, 3),  # Negative during charge
            speed_kmh=0.0,
            acceleration_mps2=0.0,
            odometer_km=round(self.state.odometer_km, 3),
            trip_distance_km=round(self.state.trip_distance_km, 3),
            energy_consumed_kwh=round(self.state.energy_consumed_kwh, 4),
            energy_consumption_kwh_per_100km=0.0,
            regenerative_energy_kwh=round(self.state.regenerative_energy_kwh, 4),
            ambient_temperature_c=round(ambient_temp, 2),
            elevation_m=round(self.state.elevation_m, 2),
            road_gradient_percent=round(gradient, 2),
            harsh_acceleration=False,
            harsh_braking=False,
            aggressive_driving_score=0.0,
            charging=True,
            charging_power_kw=round(charging_power, 3),
            charger_id=cfg.charger_id,
        )
