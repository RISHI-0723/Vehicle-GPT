"""Telemetry service for simulation and telemetry operations."""
import json
import logging
import threading
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, Tuple

from sqlalchemy.orm import Session
from sqlalchemy import desc, asc, func

from app.db.models import Vehicle, Telemetry, Simulation
from app.schemas.simulation import SimulationRequest, SimulationResponse, SimulationResetResponse
from app.simulator.engine import SimulationEngine, VehicleState, TelemetryPoint

logger = logging.getLogger(__name__)


# Simple in-process locks for same-vehicle simulation serialization
# Sprint 1 limitation: only works within single process
_simulation_locks: Dict[str, threading.Lock] = {}
_locks_lock = threading.Lock()


def _get_vehicle_lock(vehicle_id: str) -> threading.Lock:
    """Get or create a lock for a vehicle."""
    with _locks_lock:
        if vehicle_id not in _simulation_locks:
            _simulation_locks[vehicle_id] = threading.Lock()
        return _simulation_locks[vehicle_id]


class TelemetryService:
    """Service for telemetry and simulation operations."""

    def __init__(self, db: Session):
        self.db = db

    def get_telemetry(
        self,
        vehicle_id: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> Tuple[List[Telemetry], int]:
        """Get telemetry for a vehicle with filtering and pagination.

        Results are ordered newest-first (descending timestamp).

        Args:
            vehicle_id: Vehicle identifier
            start_time: Filter start time (inclusive)
            end_time: Filter end time (inclusive)
            limit: Maximum records to return
            offset: Records to skip

        Returns:
            Tuple of (telemetry list, count in response)
        """
        query = self.db.query(Telemetry).filter(Telemetry.vehicle_id == vehicle_id)

        if start_time:
            query = query.filter(Telemetry.timestamp >= start_time)
        if end_time:
            query = query.filter(Telemetry.timestamp <= end_time)

        # Order newest first
        query = query.order_by(desc(Telemetry.timestamp))

        # Apply pagination
        telemetry = query.offset(offset).limit(limit).all()

        return telemetry, len(telemetry)

    def run_simulation(self, request: SimulationRequest) -> SimulationResponse:
        """Run a simulation for a vehicle.

        Args:
            request: Simulation request parameters

        Returns:
            SimulationResponse with results

        Raises:
            ValueError: If vehicle not found or invalid parameters
            RuntimeError: If simulation already running for vehicle
        """
        # Get vehicle
        vehicle = self.db.query(Vehicle).filter(
            Vehicle.vehicle_id == request.vehicle_id
        ).first()

        if not vehicle:
            raise ValueError(f"Vehicle {request.vehicle_id} not found")

        # Acquire lock for this vehicle (non-blocking)
        vehicle_lock = _get_vehicle_lock(request.vehicle_id)
        acquired = vehicle_lock.acquire(blocking=False)

        if not acquired:
            raise RuntimeError(
                f"A simulation is already running for vehicle {request.vehicle_id}"
            )

        try:
            return self._execute_simulation(vehicle, request)
        finally:
            vehicle_lock.release()

    def _execute_simulation(
        self,
        vehicle: Vehicle,
        request: SimulationRequest,
    ) -> SimulationResponse:
        """Execute simulation within lock.

        Uses database transaction to ensure atomic commit.
        """
        logger.info(
            f"Starting simulation: vehicle={request.vehicle_id}, "
            f"scenario={request.scenario}, mode={request.mode}"
        )

        # Prepare vehicle config
        vehicle_config = {
            "vehicle_id": vehicle.vehicle_id,
            "battery_capacity_kwh": vehicle.battery_capacity_kwh,
            "usable_battery_capacity_kwh": vehicle.usable_battery_capacity_kwh,
            "initial_soc_percent": vehicle.initial_soc_percent,
            "initial_soh_percent": vehicle.initial_soh_percent,
            "initial_battery_temperature_c": vehicle.initial_battery_temperature_c,
            "initial_odometer_km": vehicle.initial_odometer_km,
        }

        # For continue mode, get previous state
        previous_state = None
        previous_timestamp = None

        if request.mode.value == "continue":
            latest = (
                self.db.query(Telemetry)
                .filter(Telemetry.vehicle_id == request.vehicle_id)
                .order_by(desc(Telemetry.timestamp))
                .first()
            )
            if latest:
                previous_state = VehicleState.from_telemetry(latest)
                previous_timestamp = latest.timestamp

        # Create and run simulation engine
        engine = SimulationEngine(
            vehicle_config=vehicle_config,
            scenario=request.scenario.value,
            duration_minutes=request.duration_minutes,
            interval_seconds=request.interval_seconds,
            seed=request.seed,
            mode=request.mode.value,
            simulation_start_time=request.simulation_start_time,
            previous_state=previous_state,
            previous_timestamp=previous_timestamp,
        )

        result = engine.run()

        # Atomic transaction: persist everything or nothing
        try:
            # Create simulation record
            summary_dict = {
                "starting_soc": result.starting_soc,
                "ending_soc": result.ending_soc,
                "starting_odometer": result.starting_odometer,
                "ending_odometer": result.ending_odometer,
                "energy_consumed": result.energy_consumed,
                "distance": result.distance,
                "average_efficiency": result.average_efficiency,
                "max_battery_temperature": result.max_battery_temperature,
                "peak_power": result.peak_power,
            }

            if result.anomaly_started_at:
                summary_dict["anomaly_started_at"] = result.anomaly_started_at.isoformat()
                summary_dict["anomaly_ended_at"] = result.anomaly_ended_at.isoformat() if result.anomaly_ended_at else None
                summary_dict["baseline_consumption"] = result.baseline_consumption
                summary_dict["anomaly_consumption"] = result.anomaly_consumption
                summary_dict["anomaly_increase_percent"] = result.anomaly_increase_percent

            simulation = Simulation(
                simulation_id=result.simulation_id,
                vehicle_id=result.vehicle_id,
                scenario=result.scenario,
                mode=result.mode,
                seed=result.seed,
                start_time=result.start_time,
                duration_minutes=result.duration_minutes,
                interval_seconds=result.interval_seconds,
                summary_json=json.dumps(summary_dict),
            )
            self.db.add(simulation)

            # Persist telemetry
            for point in result.telemetry:
                telemetry = Telemetry(
                    simulation_id=point.simulation_id,
                    vehicle_id=point.vehicle_id,
                    timestamp=point.timestamp,
                    soc_percent=point.soc_percent,
                    soh_percent=point.soh_percent,
                    battery_temperature_c=point.battery_temperature_c,
                    pack_voltage_v=point.pack_voltage_v,
                    pack_current_a=point.pack_current_a,
                    battery_power_kw=point.battery_power_kw,
                    speed_kmh=point.speed_kmh,
                    acceleration_mps2=point.acceleration_mps2,
                    odometer_km=point.odometer_km,
                    trip_distance_km=point.trip_distance_km,
                    energy_consumed_kwh=point.energy_consumed_kwh,
                    energy_consumption_kwh_per_100km=point.energy_consumption_kwh_per_100km,
                    regenerative_energy_kwh=point.regenerative_energy_kwh,
                    ambient_temperature_c=point.ambient_temperature_c,
                    elevation_m=point.elevation_m,
                    road_gradient_percent=point.road_gradient_percent,
                    harsh_acceleration=point.harsh_acceleration,
                    harsh_braking=point.harsh_braking,
                    aggressive_driving_score=point.aggressive_driving_score,
                    charging=point.charging,
                    charging_power_kw=point.charging_power_kw,
                    charger_id=point.charger_id,
                )
                self.db.add(telemetry)

            self.db.commit()
            logger.info(f"Simulation {result.simulation_id} committed successfully")

        except Exception as e:
            self.db.rollback()
            logger.error(f"Simulation {result.simulation_id} failed: {e}")
            raise

        # Build response
        return SimulationResponse(
            simulation_id=result.simulation_id,
            vehicle_id=result.vehicle_id,
            scenario=result.scenario,
            mode=result.mode,
            seed=result.seed,
            start_time=result.start_time,
            duration_minutes=result.duration_minutes,
            interval_seconds=result.interval_seconds,
            samples_generated=result.samples_generated,
            starting_soc=result.starting_soc,
            ending_soc=result.ending_soc,
            starting_odometer=result.starting_odometer,
            ending_odometer=result.ending_odometer,
            energy_consumed=result.energy_consumed,
            distance=result.distance,
            average_efficiency=result.average_efficiency,
            max_battery_temperature=result.max_battery_temperature,
            peak_power=result.peak_power,
            anomaly_started_at=result.anomaly_started_at,
            anomaly_ended_at=result.anomaly_ended_at,
            baseline_consumption=result.baseline_consumption,
            anomaly_consumption=result.anomaly_consumption,
            anomaly_increase_percent=result.anomaly_increase_percent,
        )

    def reset_vehicle(self, vehicle_id: str) -> SimulationResetResponse:
        """Reset simulation data for a vehicle.

        Deletes all telemetry and simulation history for the vehicle.
        Preserves the vehicle record itself.
        Runtime state returns to canonical baseline.

        Args:
            vehicle_id: Vehicle to reset

        Returns:
            SimulationResetResponse with deletion counts

        Raises:
            ValueError: If vehicle not found
        """
        # Verify vehicle exists
        vehicle = self.db.query(Vehicle).filter(
            Vehicle.vehicle_id == vehicle_id
        ).first()

        if not vehicle:
            raise ValueError(f"Vehicle {vehicle_id} not found")

        logger.info(f"Resetting simulation data for vehicle {vehicle_id}")

        # Count records to delete
        telemetry_count = self.db.query(func.count(Telemetry.telemetry_id)).filter(
            Telemetry.vehicle_id == vehicle_id
        ).scalar() or 0

        simulation_count = self.db.query(func.count(Simulation.simulation_id)).filter(
            Simulation.vehicle_id == vehicle_id
        ).scalar() or 0

        # Delete telemetry (must delete first due to FK constraint)
        self.db.query(Telemetry).filter(
            Telemetry.vehicle_id == vehicle_id
        ).delete(synchronize_session=False)

        # Delete simulation records
        self.db.query(Simulation).filter(
            Simulation.vehicle_id == vehicle_id
        ).delete(synchronize_session=False)

        self.db.commit()

        logger.info(
            f"Reset complete for {vehicle_id}: "
            f"{telemetry_count} telemetry, {simulation_count} simulations deleted"
        )

        return SimulationResetResponse(
            vehicle_id=vehicle_id,
            telemetry_deleted=telemetry_count,
            simulations_deleted=simulation_count,
            message=f"Vehicle {vehicle_id} reset to canonical baseline",
        )
