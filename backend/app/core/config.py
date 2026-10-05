"""Application configuration and constants."""
from pydantic_settings import BaseSettings
from typing import Optional
from datetime import datetime, timezone


class Settings(BaseSettings):
    """Application settings loaded from environment."""

    APP_NAME: str = "VehicleGPT"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = True

    # Database
    DATABASE_URL: str = "sqlite:///./data/vehiclegpt.db"

    # Simulation limits
    MAX_SIMULATION_DURATION_MINUTES: int = 480  # 8 hours max
    MAX_SIMULATION_SAMPLES: int = 10000  # Prevent accidental huge simulations
    MIN_INTERVAL_SECONDS: int = 1
    MAX_INTERVAL_SECONDS: int = 3600

    # API pagination
    DEFAULT_TELEMETRY_LIMIT: int = 100
    MAX_TELEMETRY_LIMIT: int = 1000

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()


# Canonical demo vehicle configuration - SINGLE SOURCE OF TRUTH
# These values define the immutable baseline for the demo vehicle.
# Runtime state is derived from telemetry; these values never change.
DEMO_VEHICLE_CONFIG = {
    "vehicle_id": "VG-DEMO-001",
    "make": "VehicleGPT",
    "model": "EV Demo",
    "model_year": 2026,
    "battery_capacity_kwh": 60.0,
    "usable_battery_capacity_kwh": 57.0,
    "battery_type": "LFP",
    "initial_soh_percent": 94.0,
    "initial_soc_percent": 80.0,
    "initial_battery_temperature_c": 30.0,
    "initial_odometer_km": 12500.0,
}


# Default simulation reference timestamp (timezone-aware UTC)
DEFAULT_SIMULATION_START_TIME = datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc)


# Sign conventions documentation:
# - battery_power_kw: positive = discharging, negative = charging
# - pack_current_a: positive = discharging, negative = charging
# - regenerative_energy_kwh: always non-negative
# - charging_power_kw: 0 when not charging, positive when charging
