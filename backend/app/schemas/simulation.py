"""Simulation-related Pydantic schemas."""
from datetime import datetime
from typing import Optional, List
from enum import Enum
from pydantic import BaseModel, Field, field_validator

from app.core.config import settings, DEMO_VEHICLE_CONFIG


class SimulationMode(str, Enum):
    """Simulation mode determining starting state."""

    FRESH = "fresh"  # Always starts from canonical vehicle baseline
    CONTINUE = "continue"  # Starts from latest stored telemetry


class ScenarioName(str, Enum):
    """Available simulation scenarios."""

    NORMAL_DRIVING = "NORMAL_DRIVING"
    HOT_INDIAN_DAY = "HOT_INDIAN_DAY"
    AGGRESSIVE_DRIVING = "AGGRESSIVE_DRIVING"
    FAST_CHARGING = "FAST_CHARGING"
    ENERGY_ANOMALY = "ENERGY_ANOMALY"


class SimulationRequest(BaseModel):
    """Request to run a simulation."""

    vehicle_id: str = Field(
        default=DEMO_VEHICLE_CONFIG["vehicle_id"],
        description="Vehicle to simulate",
    )
    scenario: ScenarioName = Field(..., description="Simulation scenario to run")
    duration_minutes: int = Field(
        ...,
        gt=0,
        le=settings.MAX_SIMULATION_DURATION_MINUTES,
        description="Simulation duration in minutes",
    )
    interval_seconds: int = Field(
        default=10,
        ge=settings.MIN_INTERVAL_SECONDS,
        le=settings.MAX_INTERVAL_SECONDS,
        description="Time between telemetry samples in seconds",
    )
    seed: int = Field(default=42, description="Random seed for deterministic simulation")
    mode: SimulationMode = Field(
        default=SimulationMode.FRESH,
        description="Simulation mode (fresh=baseline, continue=latest state)",
    )
    simulation_start_time: Optional[datetime] = Field(
        default=None,
        description="Custom start timestamp (ignored in continue mode)",
    )

    @field_validator("duration_minutes")
    @classmethod
    def validate_max_samples(cls, v, info):
        """Ensure simulation won't generate too many samples."""
        interval = info.data.get("interval_seconds", 10)
        samples = (v * 60) // interval
        if samples > settings.MAX_SIMULATION_SAMPLES:
            raise ValueError(
                f"Simulation would generate {samples} samples, "
                f"exceeding maximum of {settings.MAX_SIMULATION_SAMPLES}"
            )
        return v


class SimulationResponse(BaseModel):
    """Response after running a simulation."""

    simulation_id: str = Field(..., description="Unique simulation identifier")
    vehicle_id: str = Field(..., description="Vehicle that was simulated")
    scenario: str = Field(..., description="Scenario that was run")
    mode: str = Field(..., description="Simulation mode used")
    seed: int = Field(..., description="Random seed used")
    start_time: datetime = Field(..., description="Simulation start timestamp")
    duration_minutes: int = Field(..., description="Simulation duration")
    interval_seconds: int = Field(..., description="Sample interval")
    samples_generated: int = Field(..., description="Number of telemetry samples generated")

    # Summary metrics derived from actual telemetry
    starting_soc: float = Field(..., description="Starting state of charge (%)")
    ending_soc: float = Field(..., description="Ending state of charge (%)")
    starting_odometer: float = Field(..., description="Starting odometer (km)")
    ending_odometer: float = Field(..., description="Ending odometer (km)")
    energy_consumed: float = Field(..., description="Total energy consumed (kWh)")
    distance: float = Field(..., description="Total distance traveled (km)")
    average_efficiency: float = Field(..., description="Average efficiency (kWh/100km)")
    max_battery_temperature: float = Field(..., description="Maximum battery temperature (C)")
    peak_power: float = Field(..., description="Peak power demand (kW)")

    # ENERGY_ANOMALY specific fields (optional)
    anomaly_started_at: Optional[datetime] = Field(None, description="Anomaly start timestamp")
    anomaly_ended_at: Optional[datetime] = Field(None, description="Anomaly end timestamp")
    baseline_consumption: Optional[float] = Field(None, description="Baseline consumption (kWh/100km)")
    anomaly_consumption: Optional[float] = Field(None, description="Anomaly consumption (kWh/100km)")
    anomaly_increase_percent: Optional[float] = Field(None, description="Anomaly increase percentage")


class SimulationResetRequest(BaseModel):
    """Request to reset simulation data for a vehicle."""

    vehicle_id: str = Field(
        default=DEMO_VEHICLE_CONFIG["vehicle_id"],
        description="Vehicle to reset",
    )


class SimulationResetResponse(BaseModel):
    """Response after resetting simulation data."""

    vehicle_id: str = Field(..., description="Vehicle that was reset")
    telemetry_deleted: int = Field(..., description="Number of telemetry records deleted")
    simulations_deleted: int = Field(..., description="Number of simulation records deleted")
    message: str = Field(..., description="Status message")


class ScenarioInfo(BaseModel):
    """Information about a simulation scenario."""

    name: str = Field(..., description="Scenario identifier")
    description: str = Field(..., description="Human-readable scenario description")


class ScenarioListResponse(BaseModel):
    """List of available simulation scenarios."""

    scenarios: List[ScenarioInfo] = Field(..., description="Available scenarios")
