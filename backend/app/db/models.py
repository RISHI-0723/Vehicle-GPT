"""SQLAlchemy database models."""
from datetime import datetime, timezone
from sqlalchemy import (
    Column,
    String,
    Integer,
    Float,
    Boolean,
    DateTime,
    Text,
    Index,
    ForeignKey,
)
from sqlalchemy.orm import relationship

from app.db.database import Base


class Vehicle(Base):
    """Vehicle model storing canonical baseline configuration.

    This table stores the IMMUTABLE initial configuration for vehicles.
    Runtime state is derived from telemetry; these values never change
    during normal simulations.
    """

    __tablename__ = "vehicles"

    vehicle_id = Column(String(50), primary_key=True)
    make = Column(String(100), nullable=False)
    model = Column(String(100), nullable=False)
    model_year = Column(Integer, nullable=False)
    battery_capacity_kwh = Column(Float, nullable=False)
    usable_battery_capacity_kwh = Column(Float, nullable=False)
    battery_type = Column(String(50), nullable=False)
    initial_soh_percent = Column(Float, nullable=False)
    initial_soc_percent = Column(Float, nullable=False)
    initial_battery_temperature_c = Column(Float, nullable=False)
    initial_odometer_km = Column(Float, nullable=False)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    telemetry = relationship("Telemetry", back_populates="vehicle", cascade="all, delete-orphan")
    simulations = relationship("Simulation", back_populates="vehicle", cascade="all, delete-orphan")


class Telemetry(Base):
    """Telemetry model storing simulation-generated vehicle state.

    Each row represents the vehicle state at a specific simulation timestamp.
    Timestamps are SYNTHETIC SIMULATION TIME, not real wall-clock time.

    Sign conventions:
    - battery_power_kw: positive = discharging, negative = charging
    - pack_current_a: positive = discharging, negative = charging
    - regenerative_energy_kwh: always non-negative
    - charging_power_kw: 0 when not charging, positive when charging
    """

    __tablename__ = "telemetry"

    # Identity
    telemetry_id = Column(Integer, primary_key=True, autoincrement=True)
    simulation_id = Column(String(50), ForeignKey("simulations.simulation_id"), nullable=False)
    vehicle_id = Column(String(50), ForeignKey("vehicles.vehicle_id"), nullable=False)
    timestamp = Column(DateTime(timezone=True), nullable=False)

    # Battery state
    soc_percent = Column(Float, nullable=False)
    soh_percent = Column(Float, nullable=False)
    battery_temperature_c = Column(Float, nullable=False)
    pack_voltage_v = Column(Float, nullable=False)
    pack_current_a = Column(Float, nullable=False)
    battery_power_kw = Column(Float, nullable=False)

    # Vehicle state
    speed_kmh = Column(Float, nullable=False)
    acceleration_mps2 = Column(Float, nullable=False)
    odometer_km = Column(Float, nullable=False)
    trip_distance_km = Column(Float, nullable=False)

    # Energy metrics
    energy_consumed_kwh = Column(Float, nullable=False)
    energy_consumption_kwh_per_100km = Column(Float, nullable=False)
    regenerative_energy_kwh = Column(Float, nullable=False)

    # Environment
    ambient_temperature_c = Column(Float, nullable=False)
    elevation_m = Column(Float, nullable=False)
    road_gradient_percent = Column(Float, nullable=False)

    # Driving behavior
    harsh_acceleration = Column(Boolean, nullable=False, default=False)
    harsh_braking = Column(Boolean, nullable=False, default=False)
    aggressive_driving_score = Column(Float, nullable=False, default=0.0)

    # Charging state
    charging = Column(Boolean, nullable=False, default=False)
    charging_power_kw = Column(Float, nullable=False, default=0.0)
    charger_id = Column(String(50), nullable=True)

    # Relationships
    vehicle = relationship("Vehicle", back_populates="telemetry")
    simulation = relationship("Simulation", back_populates="telemetry")

    # Indexes for efficient queries
    __table_args__ = (
        Index("ix_telemetry_vehicle_timestamp", "vehicle_id", "timestamp"),
        Index("ix_telemetry_simulation", "simulation_id"),
        Index("ix_telemetry_timestamp", "timestamp"),
    )


class Simulation(Base):
    """Simulation model storing simulation run metadata and summary.

    Each simulation run is recorded with its parameters and computed summary.
    The summary is derived from actual generated telemetry.
    """

    __tablename__ = "simulations"

    simulation_id = Column(String(50), primary_key=True)
    vehicle_id = Column(String(50), ForeignKey("vehicles.vehicle_id"), nullable=False)
    scenario = Column(String(50), nullable=False)
    mode = Column(String(20), nullable=False)  # 'fresh' or 'continue'
    seed = Column(Integer, nullable=False)
    start_time = Column(DateTime(timezone=True), nullable=False)
    duration_minutes = Column(Integer, nullable=False)
    interval_seconds = Column(Integer, nullable=False)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    summary_json = Column(Text, nullable=True)  # JSON string of simulation summary

    # Relationships
    vehicle = relationship("Vehicle", back_populates="simulations")
    telemetry = relationship("Telemetry", back_populates="simulation", cascade="all, delete-orphan")
