# VehicleGPT

**AI-Powered Vehicle Intelligence Platform**

Built for the iQOO Hackathon 2026 Mobility Grand Finale.

## Important Notice

**All vehicle telemetry in this system is SYNTHETIC SIMULATED DATA.**

This is a prototype simulator. It is NOT connected to:
- Real CAN bus data
- OBD-II dongles
- OEM telemetry APIs
- Real EV battery sensors
- Any actual vehicle hardware

The simulator generates realistic-looking telemetry for demonstration and testing purposes only.

## Sprint 1: Backend Foundation

Sprint 1 implements:
- FastAPI backend with SQLite database
- Demo EV vehicle with canonical baseline configuration
- Deterministic synthetic telemetry simulator
- Five simulation scenarios
- Fresh/Continue simulation modes
- Telemetry history API with pagination
- Reset functionality
- Comprehensive test suite

## Project Structure

```
vehicle-gpt/
├── backend/
│   ├── app/
│   │   ├── api/           # API route handlers
│   │   ├── core/          # Configuration
│   │   ├── db/            # Database models
│   │   ├── schemas/       # Pydantic schemas
│   │   ├── services/      # Business logic
│   │   ├── simulator/     # Telemetry simulator
│   │   └── main.py        # FastAPI application
│   ├── tests/             # Test suite
│   └── requirements.txt   # Dependencies
├── data/                  # SQLite database
├── docs/                  # Documentation
└── README.md
```

## Quick Start

### Prerequisites

- Python 3.11 or higher

### Installation (Windows PowerShell)

```powershell
# Clone the repository
cd C:\Users\murali\Downloads\VehicleGPT

# Create virtual environment
python -m venv .venv

# Activate virtual environment
.venv\Scripts\Activate.ps1

# Install dependencies
pip install -r backend\requirements.txt
```

### Running the Backend

```powershell
# From project root with venv activated
uvicorn app.main:app --reload --app-dir backend
```

The API will be available at: http://127.0.0.1:8000

### API Documentation (Swagger)

Open in browser: http://127.0.0.1:8000/docs

### Running Tests

```powershell
# From project root with venv activated
pytest backend/tests -v
```

### Running the Frontend

```powershell
cd frontend
npm install
npm run dev
```

The app will be available at http://127.0.0.1:5173 (the backend must also be running).

```powershell
# Frontend checks
npm run typecheck
npm run test
npm run lint
npm run build
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check |
| GET | `/api/v1/vehicles` | List all vehicles |
| GET | `/api/v1/vehicles/{id}` | Get vehicle details |
| GET | `/api/v1/vehicles/{id}/state` | Get current vehicle state |
| GET | `/api/v1/vehicles/{id}/telemetry` | Get telemetry history |
| POST | `/api/v1/simulation/run` | Run a simulation |
| POST | `/api/v1/simulation/reset` | Reset simulation data |
| GET | `/api/v1/simulation/scenarios` | List available scenarios |

## Simulation Scenarios

| Scenario | Description |
|----------|-------------|
| NORMAL_DRIVING | Moderate temperature and smooth everyday driving |
| HOT_INDIAN_DAY | Hot ambient conditions (35-45°C) with increased HVAC load |
| AGGRESSIVE_DRIVING | Frequent acceleration and harsh braking |
| FAST_CHARGING | Stationary DC fast charging at 120kW |
| ENERGY_ANOMALY | Normal driving with controlled energy consumption anomaly |

## Simulation Modes

### Fresh Mode (Default)
- Always starts from canonical vehicle baseline
- Previous telemetry does not affect starting state
- Guarantees repeatable demos and tests

### Continue Mode
- Starts from latest stored telemetry state
- SOC, odometer, temperature continue from previous simulation
- Timestamp continues from previous latest + interval
- `simulation_start_time` parameter is ignored

## Telemetry Sign Conventions

| Field | Positive | Negative |
|-------|----------|----------|
| `battery_power_kw` | Discharging | Charging |
| `pack_current_a` | Discharging | Charging |
| `charging_power_kw` | Always positive when charging | N/A |
| `regenerative_energy_kwh` | Always non-negative | N/A |

## Reset Behavior

`POST /api/v1/simulation/reset`:
1. Deletes all telemetry for the vehicle
2. Deletes all simulation history
3. Preserves the vehicle record
4. Returns state to canonical baseline

## Example API Requests

### Run a Simulation

```bash
curl -X POST "http://127.0.0.1:8000/api/v1/simulation/run" \
  -H "Content-Type: application/json" \
  -d '{
    "vehicle_id": "VG-DEMO-001",
    "scenario": "NORMAL_DRIVING",
    "duration_minutes": 30,
    "interval_seconds": 10,
    "seed": 42,
    "mode": "fresh"
  }'
```

### Get Telemetry

```bash
curl "http://127.0.0.1:8000/api/v1/vehicles/VG-DEMO-001/telemetry?limit=100"
```

### Reset Vehicle

```bash
curl -X POST "http://127.0.0.1:8000/api/v1/simulation/reset" \
  -H "Content-Type: application/json" \
  -d '{"vehicle_id": "VG-DEMO-001"}'
```

## Demo Vehicle Specifications

| Property | Value |
|----------|-------|
| Vehicle ID | VG-DEMO-001 |
| Make/Model | VehicleGPT EV Demo 2026 |
| Battery Capacity | 60 kWh (57 kWh usable) |
| Battery Type | LFP |
| Initial SOH | 94% |
| Initial SOC | 80% |
| Initial Battery Temp | 30°C |
| Initial Odometer | 12,500 km |

## Sprint 1 Limitations

- Single-process concurrency only (no distributed locking)
- SOH remains constant (no degradation modeling)
- Simplified physics model (not scientific battery model)
- No authentication or production security
- Development CORS configuration

## Sprint 4: AI-Native + Phone-Native Intelligence Layer

Sprint 4 adds a local-LLM explanation layer and phone-native features on top of
the Sprint 1/2 deterministic engine -- without changing any Sprint 1/2 formula.

### Architecture

```
React (phone UI) -> FastAPI -> app/ai (intent router, intelligence bridge,
fallback formatter) -> Ollama (llama3.1:8b, local)
```

The browser never talks to Ollama directly. A driver's question is classified
by a deterministic keyword router (`app/ai/intent_router.py`, no LLM involved
in routing), the matching Sprint 2 intelligence result is fetched
(`app/ai/intelligence_bridge.py`, which only calls the existing analyzers --
it never recalculates anything), and only that structured evidence is handed
to the model to explain in natural language
(`POST /api/v1/ai/ask`, `app/ai/service.py`). The model may only write the
"answer" text; evidence, actions, and confidence always come straight from
the intelligence engine and are validated before being returned
(`app/ai/response_validator.py`). If Ollama is unavailable, times out, or
returns something malformed, a deterministic formatter
(`app/ai/fallback.py`) takes over automatically and the response reports
`"provider": "deterministic", "fallback_used": true`.

### Setting up Ollama

```powershell
# Install Ollama from https://ollama.com, then:
ollama pull llama3.1:8b
ollama serve
```

The backend performs a non-blocking health check at startup (logs
availability, never blocks or fails startup) and a short lazy check before
each AI request. No Ollama? The app still fully works via the deterministic
fallback -- every intelligence screen and the Ask screen keep functioning.

Configuration lives in `.env` (see `.env.example`): `AI_PROVIDER`,
`OLLAMA_BASE_URL`, `OLLAMA_MODEL`, `AI_TIMEOUT_SECONDS` (a total wall-clock
deadline for one Ollama call, not just a connect timeout).

### Conversation

`POST /api/v1/ai/ask` accepts a bounded `conversation` of `user`/`assistant`
turns (max 6 exchanges / 12 messages; older turns are discarded). The backend
owns the system prompt -- a frontend-supplied `"role": "system"` message is
rejected outright.

### Voice and camera (phone-native)

- **Voice**: `window.SpeechRecognition` / `webkitSpeechRecognition` only (no
  Whisper, no cloud STT, no server-side audio). Chrome/Chromium only; other
  browsers show "Voice input isn't available here."
- **Camera**: `navigator.mediaDevices.getUserMedia` for "Scan Vehicle"
  (permission, preview, capture, retake, cancel). Capturing a photo never
  implies image understanding -- there is no OCR or fault detection; the UI
  says so explicitly.

### Office Kit workflow

Real, working clipboard/share/export -- never a fake Office Kit API:
- **Copy Insight** (Why Range) / **Copy Simulation Result** (What-if): plain,
  human-readable text via the real Clipboard API, never raw JSON.
- **Export Drive Report** (Vehicle): downloads a real Markdown (`.md`) file
  with Vehicle/Simulation/Energy/Range/Intelligence/Contributors/
  Recommendations/Disclosure sections.
- **Share**: the real Web Share API when present, falling back to the
  clipboard otherwise.

### Simulation disclosure

Every AI answer carries "Based on synthetic simulated telemetry, not live
vehicle data," and the system prompt explicitly forbids claiming live
telemetry, physical connectivity, live charger availability, or battery
degradation the intelligence engine didn't report. The Vehicle screen states
plainly what is KNOWN (fixed demo config), SIMULATED (telemetry and
intelligence), and UNAVAILABLE (physical connection).

### Testing

Backend: `pytest backend/tests -v` (169 tests: the original 97 plus 72 new
Sprint 4 tests covering intent routing, conversation bounding, the Ollama
adapter's request/timeout/error handling with no live model required,
grounding/validation, tool routing, and tool-failure handling).

Frontend: `npm run test` (192 tests: the original 119 plus 73 new Sprint 4
tests covering the AI client, conversation bounding, voice and camera state
machines, office-kit formatting/export, and the updated Ask/Home/Drive/
Vehicle/WhyRange/What-if screens).

## Future Sprints

Beyond Sprint 4:
- Streaming AI responses
- On-device/offline LLM fallback model
- Battery health/degradation modeling (would require new, explicit evidence)
- Multi-vehicle support

## License

Proprietary - iQOO Hackathon 2026
