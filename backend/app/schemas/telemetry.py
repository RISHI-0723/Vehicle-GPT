"""Telemetry-related Pydantic schemas."""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict


class TelemetryBase(BaseModel):
    """Base telemetry schema with all telemetry fields.

    Sign conventions:
    - battery_power_kw: positive = discharging, negative = charging
    - pack_current_a: positive = discharging, negative = charging
    - regenerative_energy_kwh: always non-negative
    - charging_power_kw: 0 when not charging, positive when charging
    """

    # Identity
    simulation_id: str = Field(..., description="ID of the simulation that generated this data")
    vehicle_id: str = Field(..., description="Vehicle identifier")
    timestamp: datetime = Field(..., description="Simulated timestamp (UTC)")

    # Battery state
    soc_percent: float = Field(..., ge=0, le=100, description="State of charge (%)")
    soh_percent: float = Field(..., ge=0, le=100, description="State of health (%)")
    battery_temperature_c: float = Field(..., description="Battery temperature (C)")
    pack_voltage_v: float = Field(..., ge=0, description="Battery pack voltage (V)")
    pack_current_a: float = Field(..., description="Pack current (A, positive=discharge)")
    battery_power_kw: float = Field(..., description="Battery power (kW, positive=discharge)")

    # Vehicle state
    speed_kmh: float = Field(..., ge=0, description="Vehicle speed (km/h)")
    acceleration_mps2: float = Field(..., description="Acceleration (m/s^2)")
    odometer_km: float = Field(..., ge=0, description="Odometer reading (km)")
    trip_distance_km: float = Field(..., ge=0, description="Trip distance since simulation start (km)")

    # Energy metrics
    energy_consumed_kwh: float = Field(..., ge=0, description="Cumulative energy consumed (kWh)")
    energy_consumption_kwh_per_100km: float = Field(..., ge=0, description="Instantaneous consumption (kWh/100km)")
    regenerative_energy_kwh: float = Field(..., ge=0, description="Cumulative regenerated energy (kWh)")

    # Environment
    ambient_temperature_c: float = Field(..., description="Ambient temperature (C)")
    elevation_m: float = Field(..., description="Elevation above sea level (m)")
    road_gradient_percent: float = Field(..., description="Road gradient (%)")

    # Driving behavior
    harsh_acceleration: bool = Field(False, description="Harsh acceleration event flag")
    harsh_braking: bool = Field(False, description="Harsh braking event flag")
    aggressive_driving_score: float = Field(0.0, ge=0, le=100, description="Aggressive driving score (0-100)")

    # Charging state
    charging: bool = Field(False, description="Whether vehicle is charging")
    charging_power_kw: float = Field(0.0, ge=0, description="Charging power (kW, 0 when not charging)")
    charger_id: Optional[str] = Field(None, description="Charger identifier if charging")


class TelemetryResponse(TelemetryBase):
    """Telemetry response with database ID."""

    model_config = ConfigDict(from_attributes=True)

    telemetry_id: int = Field(..., description="Database telemetry record ID")


class TelemetryListResponse(BaseModel):
    """Paginated telemetry list response."""

    vehicle_id: str = Field(..., description="Vehicle identifier")
    count: int = Field(..., description="Number of items in this response")
    limit: int = Field(..., description="Requested limit")
    offset: int = Field(..., description="Requested offset")
    items: List[TelemetryResponse] = Field(..., description="Telemetry records (newest first)")
