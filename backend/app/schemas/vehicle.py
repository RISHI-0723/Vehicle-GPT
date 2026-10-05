"""Vehicle-related Pydantic schemas."""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict


class VehicleBase(BaseModel):
    """Base vehicle schema with canonical configuration."""

    model_config = ConfigDict(protected_namespaces=())

    vehicle_id: str = Field(..., description="Unique vehicle identifier")
    make: str = Field(..., description="Vehicle manufacturer")
    model: str = Field(..., description="Vehicle model name")
    model_year: int = Field(..., description="Model year")
    battery_capacity_kwh: float = Field(..., description="Total battery capacity in kWh")
    usable_battery_capacity_kwh: float = Field(..., description="Usable battery capacity in kWh")
    battery_type: str = Field(..., description="Battery chemistry type (e.g., LFP, NMC)")
    initial_soh_percent: float = Field(..., ge=0, le=100, description="Initial state of health (%)")
    initial_soc_percent: float = Field(..., ge=0, le=100, description="Initial state of charge (%)")
    initial_battery_temperature_c: float = Field(..., description="Initial battery temperature (C)")
    initial_odometer_km: float = Field(..., ge=0, description="Initial odometer reading (km)")


class VehicleResponse(VehicleBase):
    """Vehicle response with creation timestamp."""

    model_config = ConfigDict(from_attributes=True, protected_namespaces=())

    created_at: datetime = Field(..., description="Record creation timestamp")


class VehicleListResponse(BaseModel):
    """Response containing list of vehicles."""

    vehicles: List[VehicleResponse] = Field(..., description="List of vehicles")
    count: int = Field(..., description="Number of vehicles returned")


class VehicleStateResponse(BaseModel):
    """Current runtime state of a vehicle.

    If telemetry exists, this reflects the latest simulated state.
    If no telemetry exists, this reflects the canonical baseline.
    """

    model_config = ConfigDict(from_attributes=True)

    vehicle_id: str = Field(..., description="Vehicle identifier")
    timestamp: Optional[datetime] = Field(None, description="State timestamp (None if baseline)")
    soc_percent: float = Field(..., ge=0, le=100, description="Current state of charge (%)")
    soh_percent: float = Field(..., ge=0, le=100, description="Current state of health (%)")
    battery_temperature_c: float = Field(..., description="Current battery temperature (C)")
    odometer_km: float = Field(..., ge=0, description="Current odometer reading (km)")
    speed_kmh: float = Field(..., ge=0, description="Current speed (km/h)")
    battery_power_kw: float = Field(..., description="Current battery power (kW, positive=discharge)")
    charging: bool = Field(..., description="Whether vehicle is currently charging")
