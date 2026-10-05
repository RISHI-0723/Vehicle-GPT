# VehicleGPT Architecture

## Sprint 1: Backend Foundation

### System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        Mobile App (Future)                       │
└─────────────────────────────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────┐
│                     VehicleGPT Backend                           │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │                      API Layer                           │    │
│  │  /health  /vehicles  /telemetry  /simulation            │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                 │                                │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │                    Service Layer                         │    │
│  │  VehicleService  TelemetryService                       │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                 │                                │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │                  Simulation Engine                       │    │
│  │  Physics  Scenarios  Deterministic RNG                  │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                 │                                │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │                    Data Layer                            │    │
│  │  SQLAlchemy ORM  SQLite Database                        │    │
│  └─────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
```

### Data Flow

```
Simulation Request
        │
        ▼
┌───────────────┐
│  API Router   │ ──── Validation (Pydantic)
└───────────────┘
        │
        ▼
┌───────────────┐
│   Service     │ ──── Concurrency lock
└───────────────┘
        │
        ▼
┌───────────────┐
│   Engine      │ ──── Deterministic telemetry generation
└───────────────┘
        │
        ▼
┌───────────────┐
│  Database     │ ──── Atomic transaction commit
└───────────────┘
        │
        ▼
Simulation Response
```

## Data Model

### Canonical Baseline vs Runtime State

This distinction is fundamental to the system design.

```
┌─────────────────────────────────────────────────────────────────┐
│                    CANONICAL BASELINE                            │
│  Stored in: Vehicle table                                        │
│  Nature: IMMUTABLE initial configuration                         │
│  Contains:                                                       │
│    - initial_soc_percent (80%)                                   │
│    - initial_soh_percent (94%)                                   │
│    - initial_battery_temperature_c (30°C)                        │
│    - initial_odometer_km (12,500 km)                             │
│    - battery_capacity_kwh, battery_type, etc.                    │
└─────────────────────────────────────────────────────────────────┘
                                 │
                                 │ Normal simulations NEVER modify
                                 ▼
┌─────────────────────────────────────────────────────────────────┐
│                      RUNTIME STATE                               │
│  Derived from: Latest Telemetry record                           │
│  Nature: Changes with each simulation                            │
│  Reflects:                                                       │
│    - Current SOC (from latest telemetry)                         │
│    - Current battery temperature                                 │
│    - Current odometer                                            │
│    - etc.                                                        │
└─────────────────────────────────────────────────────────────────┘
                                 │
                                 │ If no telemetry exists
                                 ▼
                    Runtime state = Canonical baseline
```

### State Endpoint Logic

```python
GET /api/v1/vehicles/{id}/state

if telemetry_exists:
    return latest_telemetry_as_state()
else:
    return canonical_baseline_as_state()
```

## Simulation Modes

### Fresh Mode

```
Fresh Mode Always:
    Starting SOC = Vehicle.initial_soc_percent
    Starting Odometer = Vehicle.initial_odometer_km
    Starting Battery Temp = Vehicle.initial_battery_temperature_c

    if simulation_start_time provided:
        First timestamp = simulation_start_time
    else:
        First timestamp = 2026-01-01T00:00:00Z

    Previous telemetry is IGNORED
```

### Continue Mode

```
Continue Mode:
    Latest = max(Telemetry.timestamp) for vehicle

    if Latest exists:
        Starting SOC = Latest.soc_percent
        Starting Odometer = Latest.odometer_km
        First timestamp = Latest.timestamp + interval_seconds
    else:
        Fall back to canonical baseline
        First timestamp = 2026-01-01T00:00:00Z

    simulation_start_time parameter is IGNORED
```

### Reset Operation

```
POST /api/v1/simulation/reset

1. DELETE all Telemetry WHERE vehicle_id = X
2. DELETE all Simulation WHERE vehicle_id = X
3. PRESERVE Vehicle record
4. Runtime state now equals canonical baseline
5. Next fresh simulation is deterministic
```

## Simulation Engine

### Determinism

```
Inputs that affect output:
    - vehicle_config (from Vehicle table)
    - scenario
    - duration_minutes
    - interval_seconds
    - seed (random number generator seed)
    - mode
    - previous_state (for continue mode)
    - simulation_start_time

Given identical inputs → Identical telemetry output

Implementation:
    - LOCAL random.Random(seed) instance
    - No global random state
    - No datetime.now() for telemetry timestamps
```

### Telemetry Correlation

Telemetry fields are correlated, not independently randomized:

```
Higher speed → Higher power consumption
Higher acceleration → Higher instantaneous energy demand
Harsh acceleration → Higher aggressive driving score
Harsh braking → Regenerative energy recovery
Hot ambient → Higher battery temp, more HVAC load
Charging → speed=0, battery_power<0, SOC increases
```

### Sign Conventions

```
battery_power_kw:
    > 0  Battery discharging (driving)
    < 0  Battery charging

pack_current_a:
    > 0  Battery discharging
    < 0  Battery charging

charging_power_kw:
    = 0  Not charging
    > 0  Charging (power INTO battery)

regenerative_energy_kwh:
    >= 0  Always non-negative
```

## Database Schema

### vehicles Table

```sql
CREATE TABLE vehicles (
    vehicle_id VARCHAR(50) PRIMARY KEY,
    make VARCHAR(100) NOT NULL,
    model VARCHAR(100) NOT NULL,
    model_year INTEGER NOT NULL,
    battery_capacity_kwh FLOAT NOT NULL,
    usable_battery_capacity_kwh FLOAT NOT NULL,
    battery_type VARCHAR(50) NOT NULL,
    initial_soh_percent FLOAT NOT NULL,
    initial_soc_percent FLOAT NOT NULL,
    initial_battery_temperature_c FLOAT NOT NULL,
    initial_odometer_km FLOAT NOT NULL,
    created_at DATETIME NOT NULL
);
```

### telemetry Table

```sql
CREATE TABLE telemetry (
    telemetry_id INTEGER PRIMARY KEY AUTOINCREMENT,
    simulation_id VARCHAR(50) NOT NULL,
    vehicle_id VARCHAR(50) NOT NULL,
    timestamp DATETIME NOT NULL,
    soc_percent FLOAT NOT NULL,
    soh_percent FLOAT NOT NULL,
    battery_temperature_c FLOAT NOT NULL,
    pack_voltage_v FLOAT NOT NULL,
    pack_current_a FLOAT NOT NULL,
    battery_power_kw FLOAT NOT NULL,
    speed_kmh FLOAT NOT NULL,
    acceleration_mps2 FLOAT NOT NULL,
    odometer_km FLOAT NOT NULL,
    trip_distance_km FLOAT NOT NULL,
    energy_consumed_kwh FLOAT NOT NULL,
    energy_consumption_kwh_per_100km FLOAT NOT NULL,
    regenerative_energy_kwh FLOAT NOT NULL,
    ambient_temperature_c FLOAT NOT NULL,
    elevation_m FLOAT NOT NULL,
    road_gradient_percent FLOAT NOT NULL,
    harsh_acceleration BOOLEAN NOT NULL,
    harsh_braking BOOLEAN NOT NULL,
    aggressive_driving_score FLOAT NOT NULL,
    charging BOOLEAN NOT NULL,
    charging_power_kw FLOAT NOT NULL,
    charger_id VARCHAR(50),
    FOREIGN KEY (vehicle_id) REFERENCES vehicles(vehicle_id),
    FOREIGN KEY (simulation_id) REFERENCES simulations(simulation_id)
);

CREATE INDEX ix_telemetry_vehicle_timestamp ON telemetry(vehicle_id, timestamp);
CREATE INDEX ix_telemetry_simulation ON telemetry(simulation_id);
CREATE INDEX ix_telemetry_timestamp ON telemetry(timestamp);
```

### simulations Table

```sql
CREATE TABLE simulations (
    simulation_id VARCHAR(50) PRIMARY KEY,
    vehicle_id VARCHAR(50) NOT NULL,
    scenario VARCHAR(50) NOT NULL,
    mode VARCHAR(20) NOT NULL,
    seed INTEGER NOT NULL,
    start_time DATETIME NOT NULL,
    duration_minutes INTEGER NOT NULL,
    interval_seconds INTEGER NOT NULL,
    created_at DATETIME NOT NULL,
    summary_json TEXT,
    FOREIGN KEY (vehicle_id) REFERENCES vehicles(vehicle_id)
);
```

## Concurrency Model

Sprint 1 uses simple in-process locking:

```python
# Per-vehicle locks
_simulation_locks: Dict[str, threading.Lock]

def run_simulation(vehicle_id):
    lock = _get_vehicle_lock(vehicle_id)

    if not lock.acquire(blocking=False):
        raise HTTP 409 Conflict

    try:
        execute_simulation()
    finally:
        lock.release()
```

Limitation: Only works within single process. Distributed systems would need Redis/database locks.

## Transaction Safety

```python
# Atomic commit
try:
    db.add(simulation)
    for point in telemetry:
        db.add(point)
    db.commit()  # All or nothing
except Exception:
    db.rollback()  # No partial data
    raise
```

## Future Sprint Extensions

Sprint 2+ can add:

```
┌─────────────────────────────────────────────────────────────────┐
│                     Future Components                            │
├─────────────────────────────────────────────────────────────────┤
│  Anomaly Intelligence                                            │
│    - LLM-powered telemetry analysis                              │
│    - Pattern recognition                                         │
│    - Natural language insights                                   │
├─────────────────────────────────────────────────────────────────┤
│  Energy Prediction                                               │
│    - Route-based energy estimation                               │
│    - "What-if" simulation                                        │
├─────────────────────────────────────────────────────────────────┤
│  Battery Health Analysis                                         │
│    - SOH trend analysis                                          │
│    - Degradation predictions                                     │
├─────────────────────────────────────────────────────────────────┤
│  Charger Intelligence                                            │
│    - Optimal charging recommendations                            │
│    - Charger availability                                        │
├─────────────────────────────────────────────────────────────────┤
│  Mobile Application                                              │
│    - React Native / Flutter                                      │
│    - Voice assistant                                             │
│    - Camera AI features                                          │
└─────────────────────────────────────────────────────────────────┘
```

These are NOT implemented in Sprint 1.

## Technology Stack

| Component | Technology |
|-----------|------------|
| Web Framework | FastAPI |
| Server | Uvicorn |
| Validation | Pydantic v2 |
| ORM | SQLAlchemy 2.x |
| Database | SQLite |
| Testing | pytest, httpx |

## Directory Structure

```
vehicle-gpt/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py              # FastAPI app
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── routes_health.py
│   │   │   ├── routes_vehicle.py
│   │   │   ├── routes_simulation.py
│   │   │   └── routes_telemetry.py
│   │   ├── core/
│   │   │   ├── __init__.py
│   │   │   └── config.py
│   │   ├── db/
│   │   │   ├── __init__.py
│   │   │   ├── database.py
│   │   │   └── models.py
│   │   ├── schemas/
│   │   │   ├── __init__.py
│   │   │   ├── vehicle.py
│   │   │   ├── telemetry.py
│   │   │   └── simulation.py
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── vehicle_service.py
│   │   │   └── telemetry_service.py
│   │   └── simulator/
│   │       ├── __init__.py
│   │       ├── engine.py
│   │       ├── physics.py
│   │       └── scenarios.py
│   ├── tests/
│   │   ├── __init__.py
│   │   ├── conftest.py
│   │   ├── test_health.py
│   │   ├── test_vehicle.py
│   │   ├── test_telemetry.py
│   │   └── test_simulator.py
│   ├── requirements.txt
│   └── README.md
├── data/
│   └── .gitkeep
├── docs/
│   └── architecture.md
├── .env.example
├── .gitignore
└── README.md
```
