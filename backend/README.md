# VehicleGPT Backend

Sprint 1: Backend Foundation + Deterministic EV Telemetry Simulator

## Important Notice

**All vehicle telemetry is SYNTHETIC SIMULATED DATA.**

This simulator is NOT connected to real vehicle systems.

## Installation

```powershell
# Create and activate virtual environment
python -m venv .venv
.venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt
```

## Running the Server

```powershell
# From backend directory
uvicorn app.main:app --reload

# Or from project root
uvicorn app.main:app --reload --app-dir backend
```

Server: http://127.0.0.1:8000
Swagger: http://127.0.0.1:8000/docs

## Running Tests

```powershell
# From project root
pytest backend/tests -v

# With coverage
pytest backend/tests -v --cov=app
```

## Architecture

```
app/
├── api/                 # FastAPI route handlers
│   ├── routes_health.py
│   ├── routes_vehicle.py
│   ├── routes_telemetry.py
│   └── routes_simulation.py
├── core/
│   └── config.py        # Settings and demo vehicle config
├── db/
│   ├── database.py      # SQLAlchemy setup
│   └── models.py        # ORM models
├── schemas/
│   ├── vehicle.py       # Vehicle schemas
│   ├── telemetry.py     # Telemetry schemas
│   └── simulation.py    # Simulation schemas
├── services/
│   ├── vehicle_service.py
│   └── telemetry_service.py
├── simulator/
│   ├── physics.py       # EV physics calculations
│   ├── scenarios.py     # Scenario configurations
│   └── engine.py        # Simulation engine
└── main.py              # FastAPI application
```

## Key Concepts

### Canonical Baseline vs Runtime State

- **Canonical Baseline**: Immutable initial vehicle configuration stored in `Vehicle` table
- **Runtime State**: Current state derived from latest telemetry
- Reset removes telemetry, returning state to baseline

### Deterministic Simulation

Given identical inputs:
- vehicle baseline
- scenario
- duration
- interval
- seed
- mode
- starting state
- simulation_start_time

The output telemetry is identical.

### Simulation Modes

**Fresh**: Always starts from canonical baseline, ignoring telemetry history.

**Continue**: Starts from latest telemetry state, ignoring `simulation_start_time`.

### Sign Conventions

| Field | Positive | Negative |
|-------|----------|----------|
| `battery_power_kw` | Discharging | Charging |
| `pack_current_a` | Discharging | Charging |

## Database

SQLite database at `data/vehiclegpt.db`

Tables:
- `vehicles` - Canonical vehicle configuration
- `telemetry` - Generated telemetry points
- `simulations` - Simulation run history and summaries

## API Versioning

All endpoints use `/api/v1/` prefix.

## Configuration

Environment variables (see `.env.example`):
- `DATABASE_URL` - SQLite connection string
- `DEBUG` - Enable debug logging
