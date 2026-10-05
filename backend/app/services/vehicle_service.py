"""Vehicle service for vehicle-related operations."""
import logging
from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.db.models import Vehicle, Telemetry
from app.schemas.vehicle import VehicleStateResponse

logger = logging.getLogger(__name__)


class VehicleService:
    """Service for vehicle operations."""

    def __init__(self, db: Session):
        self.db = db

    def get_vehicle(self, vehicle_id: str) -> Optional[Vehicle]:
        """Get a vehicle by ID."""
        return self.db.query(Vehicle).filter(Vehicle.vehicle_id == vehicle_id).first()

    def get_all_vehicles(self) -> List[Vehicle]:
        """Get all vehicles."""
        return self.db.query(Vehicle).all()

    def get_vehicle_state(self, vehicle_id: str) -> Optional[VehicleStateResponse]:
        """Get current runtime state of a vehicle.

        If telemetry exists, returns the latest simulated state.
        If no telemetry exists, returns the canonical baseline state.

        Args:
            vehicle_id: Vehicle identifier

        Returns:
            VehicleStateResponse or None if vehicle not found
        """
        vehicle = self.get_vehicle(vehicle_id)
        if not vehicle:
            return None

        # Try to get latest telemetry
        latest_telemetry = (
            self.db.query(Telemetry)
            .filter(Telemetry.vehicle_id == vehicle_id)
            .order_by(desc(Telemetry.timestamp))
            .first()
        )

        if latest_telemetry:
            # Return state from latest telemetry
            return VehicleStateResponse(
                vehicle_id=vehicle_id,
                timestamp=latest_telemetry.timestamp,
                soc_percent=latest_telemetry.soc_percent,
                soh_percent=latest_telemetry.soh_percent,
                battery_temperature_c=latest_telemetry.battery_temperature_c,
                odometer_km=latest_telemetry.odometer_km,
                speed_kmh=latest_telemetry.speed_kmh,
                battery_power_kw=latest_telemetry.battery_power_kw,
                charging=latest_telemetry.charging,
            )
        else:
            # Return canonical baseline
            return VehicleStateResponse(
                vehicle_id=vehicle_id,
                timestamp=None,  # None indicates baseline state
                soc_percent=vehicle.initial_soc_percent,
                soh_percent=vehicle.initial_soh_percent,
                battery_temperature_c=vehicle.initial_battery_temperature_c,
                odometer_km=vehicle.initial_odometer_km,
                speed_kmh=0.0,
                battery_power_kw=0.0,
                charging=False,
            )
