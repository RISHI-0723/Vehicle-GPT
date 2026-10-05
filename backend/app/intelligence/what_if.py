"""What-if counterfactual engine.

This module enables counterfactual analysis by simulating
alternative scenarios from the same starting conditions.

Example: "What if I drove normally instead of aggressively?"
"""

from dataclasses import dataclass
from typing import Optional, List

from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.db.models import Simulation, Telemetry, Vehicle
from app.simulator.engine import SimulationEngine, VehicleState, SimulationResult
from app.intelligence.config import IntelligenceConfig, DEFAULT_CONFIG
from app.intelligence.features import FeatureExtractor, TelemetryFeatures


@dataclass
class WhatIfMetrics:
    """Metrics for a single scenario (base or counterfactual)."""

    scenario: str
    starting_soc_percent: float
    ending_soc_percent: float
    energy_consumed_kwh: float
    distance_km: float
    efficiency_kwh_per_100km: Optional[float]
    estimated_range_km: Optional[float]
    duration_seconds: float
    sample_count: int


@dataclass
class WhatIfResult:
    """Result of what-if counterfactual analysis."""

    # Base simulation info
    base_simulation_id: str
    base_scenario: str

    # Counterfactual info
    counterfactual_scenario: str

    # Starting state (same for both)
    starting_soc_percent: float

    # Metrics
    base_metrics: WhatIfMetrics
    counterfactual_metrics: WhatIfMetrics

    # Comparison
    energy_change_kwh: Optional[float]
    energy_change_percent: Optional[float]
    estimated_range_change_km: Optional[float]

    # Interpretation
    interpretation: str


class WhatIfEngine:
    """Counterfactual simulation engine.

    IMPORTANT STARTING-STATE SEMANTICS:
    The counterfactual MUST begin from the STARTING STATE of the base
    simulation, NOT the ending state.

    Example:
        Base simulation: starting SOC = 80%, ending SOC = 52%
        "What if I drove normally?"
        Counterfactual starts from 80%, NOT 52%

    This ensures the comparison represents:
        same starting conditions + different driving behavior

    IMPORTANT:
    - Counterfactual simulation does NOT persist telemetry
    - This is a side-effect-free analysis tool
    - FAST_CHARGING counterfactual: estimated_range_change is null
    """

    # Scenarios suitable for driving analysis
    DRIVING_SCENARIOS = {"NORMAL_DRIVING", "HOT_INDIAN_DAY", "AGGRESSIVE_DRIVING", "ENERGY_ANOMALY"}

    def __init__(self, db: Session, config: IntelligenceConfig = DEFAULT_CONFIG):
        """Initialize what-if engine.

        Args:
            db: Database session
            config: Intelligence configuration
        """
        self.db = db
        self.config = config
        self.feature_extractor = FeatureExtractor(config)

    def run_counterfactual(
        self,
        vehicle_id: str,
        counterfactual_scenario: str,
        base_simulation_id: Optional[str] = None,
        duration_minutes: Optional[int] = None,
        interval_seconds: Optional[int] = None,
        seed: int = 42,
    ) -> WhatIfResult:
        """Run a what-if counterfactual analysis.

        Args:
            vehicle_id: Vehicle to analyze
            counterfactual_scenario: Scenario to simulate as alternative
            base_simulation_id: Base simulation (optional, defaults to latest suitable)
            duration_minutes: Duration (optional, inherits from base)
            interval_seconds: Interval (optional, inherits from base)
            seed: Random seed for counterfactual

        Returns:
            WhatIfResult with comparison

        Raises:
            ValueError: If vehicle or base simulation not found
        """
        # Get vehicle
        vehicle = self.db.query(Vehicle).filter(Vehicle.vehicle_id == vehicle_id).first()
        if not vehicle:
            raise ValueError(f"Vehicle not found: {vehicle_id}")

        # Get base simulation
        if base_simulation_id:
            base_sim = (
                self.db.query(Simulation)
                .filter(Simulation.simulation_id == base_simulation_id)
                .first()
            )
            if not base_sim:
                raise ValueError(f"Simulation not found: {base_simulation_id}")
        else:
            # Find latest suitable driving simulation
            base_sim = self._find_latest_driving_simulation(vehicle_id)
            if not base_sim:
                raise ValueError(f"No suitable driving simulation found for vehicle: {vehicle_id}")

        # Get base simulation telemetry
        base_telemetry = (
            self.db.query(Telemetry)
            .filter(Telemetry.simulation_id == base_sim.simulation_id)
            .order_by(Telemetry.timestamp)
            .all()
        )

        if not base_telemetry:
            raise ValueError(f"No telemetry found for simulation: {base_sim.simulation_id}")

        # Inherit duration/interval from base if not specified
        actual_duration = duration_minutes or base_sim.duration_minutes
        actual_interval = interval_seconds or base_sim.interval_seconds

        # Build vehicle config (canonical baseline, same shape as Sprint 1 simulation service)
        vehicle_config = {
            "vehicle_id": vehicle.vehicle_id,
            "battery_capacity_kwh": vehicle.battery_capacity_kwh,
            "usable_battery_capacity_kwh": vehicle.usable_battery_capacity_kwh,
            "initial_soc_percent": vehicle.initial_soc_percent,
            "initial_soh_percent": vehicle.initial_soh_percent,
            "initial_battery_temperature_c": vehicle.initial_battery_temperature_c,
            "initial_odometer_km": vehicle.initial_odometer_km,
        }

        # State immediately BEFORE the base simulation began (not its first telemetry sample)
        starting_state = self._resolve_starting_state(vehicle_config, base_sim)

        # Run counterfactual simulation (in-memory, NOT persisted)
        counterfactual_engine = SimulationEngine(
            vehicle_config=vehicle_config,
            scenario=counterfactual_scenario,
            duration_minutes=actual_duration,
            interval_seconds=actual_interval,
            seed=seed,
            mode="fresh",  # Fresh mode, but from the explicit starting state below
            simulation_start_time=base_sim.start_time,
            initial_state=starting_state,
        )

        counterfactual_result = counterfactual_engine.run()

        # Extract features from both
        base_features = self.feature_extractor.extract(base_telemetry)
        counterfactual_features = self._extract_features_from_result(counterfactual_result)

        # Build metrics
        base_metrics = self._build_metrics(
            base_sim.scenario,
            base_features,
            starting_state.soc_percent,
        )

        counterfactual_metrics = self._build_metrics(
            counterfactual_scenario,
            counterfactual_features,
            starting_state.soc_percent,
        )

        # Calculate comparison
        energy_change, energy_change_percent, range_change = self._calculate_comparison(
            base_metrics, counterfactual_metrics, counterfactual_scenario
        )

        # Generate interpretation
        interpretation = self._generate_interpretation(
            base_sim.scenario,
            counterfactual_scenario,
            energy_change,
            energy_change_percent,
            range_change,
        )

        return WhatIfResult(
            base_simulation_id=base_sim.simulation_id,
            base_scenario=base_sim.scenario,
            counterfactual_scenario=counterfactual_scenario,
            starting_soc_percent=round(starting_state.soc_percent, self.config.percentage_precision),
            base_metrics=base_metrics,
            counterfactual_metrics=counterfactual_metrics,
            energy_change_kwh=self._round_optional(energy_change, self.config.energy_precision),
            energy_change_percent=self._round_optional(energy_change_percent, self.config.percentage_precision),
            estimated_range_change_km=self._round_optional(range_change, self.config.distance_precision),
            interpretation=interpretation,
        )

    def _resolve_starting_state(
        self,
        vehicle_config: dict,
        base_sim: Simulation,
    ) -> VehicleState:
        """Return the vehicle state immediately BEFORE the base simulation began.

        Mirrors how Sprint 1 starts simulations:
        - fresh base: the canonical baseline (SimulationEngine's fresh-mode state)
        - continue base: the last telemetry recorded before the base started
          (the state continue mode resumes from; falls back to the baseline
          when no earlier telemetry exists, as the Sprint 1 service does)

        Args:
            vehicle_config: Canonical vehicle configuration
            base_sim: Base simulation

        Returns:
            VehicleState for the counterfactual to start from
        """
        if base_sim.mode == "continue":
            previous = (
                self.db.query(Telemetry)
                .filter(Telemetry.vehicle_id == base_sim.vehicle_id)
                .filter(Telemetry.timestamp < base_sim.start_time)
                .order_by(desc(Telemetry.timestamp))
                .first()
            )
            if previous:
                return VehicleState.from_telemetry(previous)

        return VehicleState.from_baseline(vehicle_config)

    def _find_latest_driving_simulation(self, vehicle_id: str) -> Optional[Simulation]:
        """Find the latest suitable driving simulation.

        Args:
            vehicle_id: Vehicle to find simulation for

        Returns:
            Latest driving simulation or None
        """
        return (
            self.db.query(Simulation)
            .filter(Simulation.vehicle_id == vehicle_id)
            .filter(Simulation.scenario.in_(self.DRIVING_SCENARIOS))
            .order_by(desc(Simulation.created_at))
            .first()
        )

    def _extract_features_from_result(self, result: SimulationResult) -> TelemetryFeatures:
        """Extract features from in-memory simulation result.

        We need to convert TelemetryPoint dataclass to match what
        the feature extractor expects. Create a simple adapter.
        """
        # Create mock telemetry objects that have the required attributes
        class MockTelemetry:
            def __init__(self, point):
                self.timestamp = point.timestamp
                self.soc_percent = point.soc_percent
                self.soh_percent = point.soh_percent
                self.battery_temperature_c = point.battery_temperature_c
                self.pack_voltage_v = point.pack_voltage_v
                self.pack_current_a = point.pack_current_a
                self.battery_power_kw = point.battery_power_kw
                self.speed_kmh = point.speed_kmh
                self.acceleration_mps2 = point.acceleration_mps2
                self.odometer_km = point.odometer_km
                self.trip_distance_km = point.trip_distance_km
                self.energy_consumed_kwh = point.energy_consumed_kwh
                self.energy_consumption_kwh_per_100km = point.energy_consumption_kwh_per_100km
                self.regenerative_energy_kwh = point.regenerative_energy_kwh
                self.ambient_temperature_c = point.ambient_temperature_c
                self.elevation_m = point.elevation_m
                self.road_gradient_percent = point.road_gradient_percent
                self.harsh_acceleration = point.harsh_acceleration
                self.harsh_braking = point.harsh_braking
                self.aggressive_driving_score = point.aggressive_driving_score
                self.charging = point.charging
                self.charging_power_kw = point.charging_power_kw
                self.charger_id = point.charger_id

        mock_telemetry = [MockTelemetry(p) for p in result.telemetry]
        return self.feature_extractor.extract(mock_telemetry)

    def _build_metrics(
        self,
        scenario: str,
        features: TelemetryFeatures,
        starting_soc: float,
    ) -> WhatIfMetrics:
        """Build metrics from features.

        Args:
            scenario: Scenario name
            features: Extracted features
            starting_soc: Starting SOC

        Returns:
            WhatIfMetrics object
        """
        # Calculate estimated range if we have efficiency
        estimated_range = None
        if features.energy_per_km is not None and features.energy_per_km > self.config.epsilon:
            remaining_energy = (
                self.config.usable_battery_capacity_kwh * (features.ending_soc_percent / 100)
            )
            estimated_range = remaining_energy / features.energy_per_km

        return WhatIfMetrics(
            scenario=scenario,
            starting_soc_percent=round(starting_soc, self.config.percentage_precision),
            ending_soc_percent=round(features.ending_soc_percent, self.config.percentage_precision),
            energy_consumed_kwh=round(features.energy_consumed_kwh, self.config.energy_precision),
            distance_km=round(features.distance_km, self.config.distance_precision),
            efficiency_kwh_per_100km=self._round_optional(
                features.efficiency_kwh_per_100km, self.config.energy_precision
            ),
            estimated_range_km=self._round_optional(estimated_range, self.config.distance_precision),
            duration_seconds=features.duration_seconds,
            sample_count=features.sample_count,
        )

    def _calculate_comparison(
        self,
        base: WhatIfMetrics,
        counterfactual: WhatIfMetrics,
        counterfactual_scenario: str,
    ) -> tuple[Optional[float], Optional[float], Optional[float]]:
        """Calculate comparison metrics between base and counterfactual.

        Args:
            base: Base scenario metrics
            counterfactual: Counterfactual scenario metrics
            counterfactual_scenario: Name of counterfactual scenario

        Returns:
            Tuple of (energy_change, energy_change_percent, range_change)
        """
        # Energy change
        energy_change = None
        energy_change_percent = None
        if base.energy_consumed_kwh > self.config.epsilon:
            energy_change = counterfactual.energy_consumed_kwh - base.energy_consumed_kwh
            energy_change_percent = (energy_change / base.energy_consumed_kwh) * 100

        # Range change - ONLY for driving scenarios
        range_change = None
        if counterfactual_scenario != "FAST_CHARGING":
            if base.estimated_range_km is not None and counterfactual.estimated_range_km is not None:
                range_change = counterfactual.estimated_range_km - base.estimated_range_km

        return energy_change, energy_change_percent, range_change

    def _generate_interpretation(
        self,
        base_scenario: str,
        counterfactual_scenario: str,
        energy_change: Optional[float],
        energy_change_percent: Optional[float],
        range_change: Optional[float],
    ) -> str:
        """Generate human-readable interpretation.

        Args:
            base_scenario: Original scenario
            counterfactual_scenario: Alternative scenario
            energy_change: Energy difference (kWh)
            energy_change_percent: Energy difference (%)
            range_change: Range difference (km)

        Returns:
            Interpretation string
        """
        if counterfactual_scenario == "FAST_CHARGING":
            return (
                f"Counterfactual charging scenario simulated. "
                f"Range comparison not applicable for charging sessions."
            )

        if energy_change is None or energy_change_percent is None:
            return (
                f"Simulated {counterfactual_scenario} instead of {base_scenario}. "
                f"Energy comparison unavailable due to insufficient data."
            )

        # Describe energy change
        if abs(energy_change_percent) < 2:
            energy_desc = "similar energy consumption"
        elif energy_change < 0:
            energy_desc = f"{abs(energy_change_percent):.1f}% less energy consumed"
        else:
            energy_desc = f"{energy_change_percent:.1f}% more energy consumed"

        # Describe range change
        if range_change is None:
            range_desc = ""
        elif abs(range_change) < 1:
            range_desc = " with similar estimated range"
        elif range_change > 0:
            range_desc = f" with approximately {range_change:.1f} km more estimated range"
        else:
            range_desc = f" with approximately {abs(range_change):.1f} km less estimated range"

        return (
            f"If you had driven with {counterfactual_scenario} instead of {base_scenario}, "
            f"the counterfactual shows {energy_desc}{range_desc}."
        )

    def _round_optional(self, value: Optional[float], precision: int) -> Optional[float]:
        """Round a value if not None."""
        if value is None:
            return None
        return round(value, precision)
