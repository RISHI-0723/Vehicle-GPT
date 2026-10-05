# VehicleGPT

> **A phone-first intelligence layer for EVs that turns vehicle telemetry into explanations, counterfactual simulations, and actionable recommendations.**

Built for the **iQOO Hackathon 2026 — Mobility Grand Finale**.

**Product loop:**  
**DETECT → EXPLAIN → SIMULATE → RECOMMEND**

---

## Why VehicleGPT?

EVs already expose a large amount of data: state of charge, temperature, power demand, energy consumption, regeneration, speed, and more.

The problem is that a driver usually gets **numbers, not understanding**.

VehicleGPT is designed as an intelligence layer between vehicle data and the driver:

```text
Vehicle data
    ↓
Deterministic vehicle intelligence
    ↓
Intent understanding
    ↓
Evidence-grounded AI explanation
    ↓
Phone-first driver experience
```

The prototype demonstrates questions such as:

- **Why did my range drop?**
- **What caused this drive to be inefficient?**
- **What if I drove normally instead?**
- **Is my battery under operating stress?**
- **What should I change?**
- **How much did this drive cost?**

The key experience is not just explaining the past. VehicleGPT can also run a **deterministic counterfactual simulation** to show what could have happened under a different driving scenario.

---

# ⚠️ Prototype Disclosure

This repository is a **working software prototype**.

The current vehicle telemetry is **synthetic, deterministic simulation data**. The prototype is **not connected to a physical EV**.

It does not currently connect to:

- CAN bus
- OBD-II hardware
- OEM vehicle APIs
- real battery sensors
- a physical vehicle
- live charger availability

The purpose of the simulator is to provide a reproducible vehicle-data source so the complete intelligence workflow can be demonstrated without requiring proprietary OEM access or physical hardware.

The intended production architecture is:

```text
Production:
EV / OEM API / Telematics
            ↓
    VehicleGPT Intelligence
            ↓
        Driver Phone

Current Prototype:
Deterministic EV Simulator
            ↓
    VehicleGPT Intelligence
            ↓
        Driver Phone
```

**The simulator is the data source. The intelligence layer is the product.**

---

# ✨ What the Prototype Does

## 1. Explain a Drive

VehicleGPT analyzes a completed simulated drive and produces:

- energy consumed
- energy regenerated
- net energy
- efficiency
- estimated range
- anomaly score
- operating battery stress
- temperature exposure
- contributor analysis
- prioritized recommendations

---

## 2. Answer Driver Questions

The phone provides a natural-language interface through:

```text
POST /api/v1/ai/ask
```

Supported deterministic intents include:

- `RANGE_DROP`
- `ENERGY_EFFICIENCY`
- `BATTERY_STRESS`
- `ANOMALY`
- `COST`
- `WHAT_IF`
- `RECOMMENDATIONS`
- `DRIVE_COMPARISON`
- `GENERAL_VEHICLE`
- `UNKNOWN`

The intent router does **not** depend on an LLM.

---

## 3. Evidence-Grounded Local AI

VehicleGPT uses:

**Ollama + llama3.1:8b**

The browser never talks directly to Ollama.

```text
React
  ↓
FastAPI
  ↓
Deterministic intent router
  ↓
Existing vehicle intelligence
  ↓
Structured evidence
  ↓
Ollama
  ↓
Validated explanation
  ↓
Phone
```

The LLM is responsible for **language**, not vehicle calculations.

It does not calculate:

- range
- efficiency
- energy
- anomaly scores
- battery stress
- cost
- wear

Those remain deterministic backend calculations.

If Ollama is unavailable, times out, or produces malformed output, VehicleGPT automatically falls back to a deterministic explanation.

---

# 🧠 AI Grounding

VehicleGPT intentionally separates **truth** from **language generation**.

```text
DETERMINISTIC ENGINE
        │
        ├── metrics
        ├── contributors
        ├── confidence
        ├── recommendations
        └── simulation results
                 │
                 ▼
              Ollama
                 │
                 ▼
        Natural-language explanation
```

The AI cannot:

- invent vehicle metrics
- upgrade confidence
- claim physical vehicle connectivity
- claim live telemetry
- claim live charger availability
- claim battery degradation without evidence
- invent electricity prices

Evidence, actions, confidence, and intent are controlled by the backend.

---

# 🔥 Hero Feature — Counterfactual Driving

The strongest demonstration is:

> **“Why did my range drop?”**

followed by:

> **“What if I drove normally?”**

VehicleGPT compares the aggressive drive against a deterministic normal-driving counterfactual.

This creates the product loop:

```text
WHAT HAPPENED?
      ↓
WHY?
      ↓
WHAT IF?
      ↓
WHAT SHOULD I CHANGE?
```

The What-if result is explicitly presented as a **simulation/counterfactual**, not a prediction.

---

# 📱 Why This Belongs on a Phone

VehicleGPT is deliberately phone-first.

The phone is the driver's intelligence interface rather than another dashboard.

### Phone-native capabilities

**Ask**
- Natural-language vehicle questions
- Multi-turn conversation
- Suggested questions

**Voice**
- Browser Web Speech API
- Chrome/Chromium
- Voice → transcript → vehicle question

**Camera**
- Browser camera capture
- Scan/capture/retake/cancel
- Explicitly does not fake image understanding

**Touch**
- Large mobile controls
- Bottom navigation
- One-tap What-if actions

**Office workflow**
- Copy insight
- Copy simulation result
- Share
- Export a Markdown drive report

The phone does not pretend to be the vehicle sensor.

It is the place where vehicle intelligence becomes **understandable and actionable for the driver**.

---

# 📲 Main Screens

| Screen | Purpose |
|---|---|
| **Home** | Current demo drive, range, explanation, key intelligence and next action |
| **Ask** | Natural-language VehicleGPT assistant |
| **Drive** | Inspect and understand the latest simulated drive |
| **Vehicle** | Vehicle configuration and data truth model |
| **Why Range** | Evidence behind range change |
| **What-if** | Counterfactual driving simulation |
| **Cost** | Electricity-price-based operating cost |
| **Demo Setup** | Prepare/reset canonical demonstration data |

---

# 🎬 Canonical Demo

The reproducible demo vehicle is:

| Property | Value |
|---|---|
| Vehicle ID | `VG-DEMO-001` |
| Vehicle | VehicleGPT EV Demo 2026 |
| Battery | 60 kWh |
| Usable battery | 57 kWh |
| Battery type | LFP |
| Initial SOC | 80% |
| Initial SOH | 94% |
| Initial battery temperature | 30°C |
| Initial odometer | 12,500 km |

Canonical demo simulations:

```text
1. NORMAL_DRIVING
2. AGGRESSIVE_DRIVING
```

Both use:

```text
seed = 42
duration = 30 minutes
interval = 10 seconds
mode = fresh
simulation_start_time = 2026-01-01T00:00:00Z
```

The canonical setup creates the normal drive first, then the aggressive drive, and verifies the persisted simulation history before the main app becomes available.

---

# 🏗️ Architecture

```text
┌─────────────────────────────────────────────┐
│                 PHONE UI                    │
│                                             │
│ Home · Ask · Drive · Vehicle · What-if      │
│ Cost · Voice · Camera · Share · Export      │
└──────────────────────┬──────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────┐
│              React / Vite / TS              │
└──────────────────────┬──────────────────────┘
                       │ HTTP
                       ▼
┌─────────────────────────────────────────────┐
│               FastAPI Backend               │
│                                             │
│  Vehicle / Simulation / Telemetry APIs      │
│  Deterministic Intelligence APIs            │
│  AI Ask API                                 │
└───────────────┬─────────────────────────────┘
                │
       ┌────────┴───────────┐
       ▼                    ▼
┌───────────────┐    ┌─────────────────────┐
│ EV Simulator  │    │ Intelligence Engine │
│               │    │                     │
│ scenarios     │    │ energy              │
│ telemetry     │    │ range               │
│ fresh/continue│    │ anomaly             │
└───────────────┘    │ battery stress      │
                     │ contributors        │
                     │ recommendations     │
                     │ what-if             │
                     │ cost                │
                     └──────────┬──────────┘
                                │
                                ▼
                     ┌─────────────────────┐
                     │ AI Explanation      │
                     │                     │
                     │ Intent Router       │
                     │ Evidence Builder    │
                     │ Ollama Adapter      │
                     │ Response Validator  │
                     │ Deterministic       │
                     │ Fallback             │
                     └─────────────────────┘
```

---

# 🧩 Technology Stack

## Frontend

- React 19
- TypeScript
- Vite
- React Router
- Lucide React
- Vitest
- React Testing Library
- jsdom

## Backend

- Python 3.11+
- FastAPI
- Pydantic
- SQLAlchemy
- SQLite
- pytest
- httpx

## AI

- Ollama
- `llama3.1:8b`
- Server-side inference
- Deterministic fallback

## Phone-native Web APIs

- Web Speech API
- `navigator.mediaDevices.getUserMedia`
- Clipboard API
- Web Share API
- Browser download APIs

---

# 🔌 API Surface

## Vehicle

```text
GET  /api/v1/vehicles
GET  /api/v1/vehicles/{vehicle_id}
GET  /api/v1/vehicles/{vehicle_id}/state
GET  /api/v1/vehicles/{vehicle_id}/telemetry
```

## Simulation

```text
POST /api/v1/simulation/run
POST /api/v1/simulation/reset
GET  /api/v1/simulation/scenarios
```

## Intelligence

```text
GET  /api/v1/intelligence/energy/{vehicle_id}
GET  /api/v1/intelligence/range/{vehicle_id}
GET  /api/v1/intelligence/anomaly/{vehicle_id}
GET  /api/v1/intelligence/battery-stress/{vehicle_id}
GET  /api/v1/intelligence/contributors/{vehicle_id}
GET  /api/v1/intelligence/recommendations/{vehicle_id}
GET  /api/v1/intelligence/why-range-dropped/{vehicle_id}
GET  /api/v1/intelligence/summary/{vehicle_id}

POST /api/v1/intelligence/what-if
POST /api/v1/intelligence/cost
```

## AI

```text
POST /api/v1/ai/ask
```

## Health

```text
GET /health
```

Interactive API documentation:

```text
http://127.0.0.1:8000/docs
```

---

# 🧪 Testing

The project has a layered automated test strategy.

### Latest validated regression

```text
Backend:  169 passed
Frontend: 194 passed
Total:    363 passed
```

The backend suite covers:

- simulator behavior
- vehicle APIs
- telemetry
- intelligence formulas
- baseline selection
- anomaly detection
- battery stress
- What-if
- cost
- recommendations
- AI intent routing
- conversation limits
- Ollama adapter
- grounding
- response validation
- AI endpoint failures

The frontend suite covers:

- API client
- routing
- demo bootstrap
- canonical demo resolution
- AI conversation
- Ask
- Home
- Drive
- Vehicle
- Why Range
- What-if
- Cost
- voice state machine
- camera state machine
- AnswerCard
- export/share/copy workflows

Run:

```powershell
# Backend
pytest backend/tests -v

# Frontend
cd frontend
npm run typecheck
npm run test
npm run lint
npm run build
```

---

# 🚀 Quick Start

## 1. Backend

From the repository root:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r backend\requirements.txt
```

Start FastAPI:

```powershell
uvicorn app.main:app --reload --app-dir backend
```

Backend:

```text
http://127.0.0.1:8000
```

Swagger:

```text
http://127.0.0.1:8000/docs
```

---

## 2. Ollama

Install Ollama and pull the configured model:

```powershell
ollama pull llama3.1:8b
```

Run Ollama if required by your installation:

```powershell
ollama serve
```

Default configuration:

```text
OLLAMA_BASE_URL=http://127.0.0.1:11434
OLLAMA_MODEL=llama3.1:8b
AI_TIMEOUT_SECONDS=20
```

If Ollama is unavailable, VehicleGPT automatically uses its deterministic fallback.

---

## 3. Frontend

```powershell
cd frontend
npm install
npm run dev
```

Frontend:

```text
http://127.0.0.1:5173
```

Set:

```text
VITE_API_BASE_URL=http://127.0.0.1:8000
```

in `frontend/.env` if needed.

---

# 🎤 Judge Demo — Recommended 5–7 Minute Flow

Do **not** start by explaining the architecture.

Start with the problem.

### 1. Hook

> “Your EV can tell you what happened. But it doesn't always tell you why.”

Open VehicleGPT on the phone.

### 2. Establish the product

> “VehicleGPT is a phone-first intelligence layer for EV drivers.”

Briefly point out:

**Simulation Mode / Synthetic Telemetry**

Do not hide this.

### 3. Hero question

Ask:

> **Why did my range drop?**

Show the explanation and evidence.

Say:

> “Instead of giving the driver another number, VehicleGPT explains the factors behind it.”

### 4. Counterfactual — the killer moment

Ask:

> **What if I drove normally?**

Run the simulation.

Show:

```text
Aggressive drive
        vs
Normal-driving counterfactual
```

Say:

> “Now it doesn't just explain the past. It simulates an alternative.”

### 5. Recommendation

Ask:

> **What should I change?**

Show prioritized recommendations.

### 6. Cost

Ask:

> **How much did that aggressive drive cost me?**

If needed, enter an electricity price.

Say:

> “The system never invents a price — the driver supplies the electricity tariff.”

### 7. Phone-native features

Quickly demonstrate:

- voice question
- camera capture
- share/copy
- drive report export

Do not spend too much time here.

### 8. Close with the architecture

> “For this prototype, vehicle telemetry is deterministic simulated data. That gives us a reproducible vehicle-data source without requiring a physical EV or proprietary OEM access.”

Then:

> “The simulator can be replaced by an OEM, telematics, or compatible vehicle data source. The intelligence layer remains the same.”

Finish with:

> **“We're not building another vehicle dashboard. We're building the intelligence layer that makes vehicle data understandable and actionable.”**

---

# 🏆 What Judges Should Remember

VehicleGPT demonstrates five things:

### 1. Understand

It understands structured vehicle telemetry.

### 2. Explain

It turns vehicle intelligence into a driver-friendly explanation.

### 3. Simulate

It answers “what if?” with a deterministic counterfactual.

### 4. Recommend

It converts analysis into actions.

### 5. Deliver on the phone

The driver interacts through a phone-first experience rather than another dashboard.

---

# 🔐 Design Principles

VehicleGPT intentionally follows these rules:

1. **Evidence before language**
2. **Deterministic calculations before AI**
3. **AI explains; AI does not invent**
4. **Simulation is always disclosed**
5. **No fake vehicle connectivity**
6. **No fake live telemetry**
7. **No hidden electricity price**
8. **No fabricated sensor data**
9. **Graceful AI fallback**
10. **Phone-first interaction**

---

# 📁 Repository Structure

```text
VehicleGPT/
├── backend/
│   ├── app/
│   │   ├── ai/
│   │   ├── api/
│   │   ├── core/
│   │   ├── db/
│   │   ├── intelligence/
│   │   ├── schemas/
│   │   ├── services/
│   │   ├── simulator/
│   │   └── main.py
│   ├── tests/
│   └── requirements.txt
│
├── frontend/
│   ├── src/
│   │   ├── ai/
│   │   ├── api/
│   │   ├── camera/
│   │   ├── components/
│   │   ├── demo/
│   │   ├── office/
│   │   ├── pages/
│   │   ├── voice/
│   │   └── main.tsx
│   ├── package.json
│   └── vite.config.ts
│
├── data/
├── docs/
├── .env.example
├── SPRINT_4_REPORT.md
└── README.md
```

---

# ⚠️ Repository Hygiene

Do **not** commit generated/local dependencies such as:

```text
.venv/
frontend/node_modules/
__pycache__/
.pytest_cache/
.env
*.db
frontend/dist/
```

The repository's `.gitignore` already excludes the main categories.

Before pushing to GitHub, verify:

```powershell
git status
```

and make sure local environments, databases, and generated dependencies are not being committed.

---

# 🛣️ Future Production Direction

The prototype deliberately stops short of claiming production vehicle connectivity.

A production version could add:

```text
OEM / Telematics / Compatible Vehicle Data
                ↓
       VehicleGPT Data Adapter
                ↓
       Existing Intelligence Layer
                ↓
       AI Explanation Layer
                ↓
             Phone
```

Potential future work:

- OEM integrations
- multi-vehicle support
- streaming responses
- on-device/offline AI
- explicit battery health/degradation modeling
- richer phone sensor integrations
- production authentication/security

These are future capabilities, not claims about the current prototype.

---

# 📜 License

Proprietary — iQOO Hackathon 2026.
