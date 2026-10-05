"""VehicleGPT Backend - Main FastAPI Application.

This is the main entry point for the VehicleGPT backend API.
Sprint 1: Backend Foundation + Deterministic EV Telemetry Simulator
Sprint 2: Deterministic Intelligence Engine

IMPORTANT: All vehicle telemetry in this system is SYNTHETIC SIMULATED DATA.
This is a prototype simulator, not connected to real vehicle systems.
"""
import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.db.database import init_db
from app.api import (
    health_router,
    vehicle_router,
    telemetry_router,
    simulation_router,
    intelligence_router,
    ai_router,
)
from app.ai.ollama_client import check_ollama_available


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


#: Short startup-probe timeout. This only produces a log line, so it must stay
#: cheap: a blocked/firewalled connect attempt (common for an unused local
#: port) can otherwise take seconds to fail, which would multiply across
#: every app instance (e.g. the test suite's one-per-test TestClient).
STARTUP_HEALTH_CHECK_TIMEOUT_SECONDS = 0.3


async def _log_ollama_availability() -> None:
    """Runs in the background so a slow/unreachable Ollama can never delay startup."""
    try:
        if await check_ollama_available(timeout_seconds=STARTUP_HEALTH_CHECK_TIMEOUT_SECONDS):
            logger.info("VehicleGPT AI provider: Ollama available")
        else:
            logger.info("VehicleGPT AI provider: Ollama unavailable — deterministic fallback enabled")
    except Exception:
        logger.info("VehicleGPT AI provider: Ollama unavailable — deterministic fallback enabled")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    init_db()

    # Fire-and-forget AI provider health check: scheduled, never awaited, so a
    # slow or unreachable Ollama cannot delay or block FastAPI startup.
    # Availability is also re-checked lazily before every AI request, since
    # it can change at any time after startup.
    health_check_task = asyncio.create_task(_log_ollama_availability())

    logger.info("Application startup complete")

    yield

    # Shutdown
    health_check_task.cancel()
    logger.info("Application shutting down")


# Create FastAPI application
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="""
## VehicleGPT Backend API

Sprint 1: Backend Foundation + Deterministic EV Telemetry Simulator
Sprint 2: Deterministic Intelligence Engine

### Important Notice
**All vehicle telemetry in this system is SYNTHETIC SIMULATED DATA.**
This is a prototype simulator built for the iQOO Hackathon 2026 Mobility Grand Finale.
It is NOT connected to real vehicle systems, OBD, CAN bus, or OEM telemetry.

### Sprint 1 Features
- Demo EV vehicle with canonical baseline configuration
- Deterministic telemetry simulation with 5 scenarios
- Fresh/Continue simulation modes
- Telemetry history with pagination and filtering
- Reset functionality

### Sprint 2 Features (Intelligence Engine)
- Energy analysis with baseline comparison
- Range estimation based on recent efficiency
- Contributor analysis for efficiency differences
- Anomaly detection with weighted scoring
- Battery stress analysis (operational stress, not SOH)
- What-if counterfactual simulation
- Cost-of-driving analysis with wear proxy
- Actionable recommendations
- Composite "Why did my range drop?" analysis

### Sign Conventions
- `battery_power_kw`: positive = discharging, negative = charging
- `pack_current_a`: positive = discharging, negative = charging
- `regenerative_energy_kwh`: always non-negative
- `charging_power_kw`: 0 when not charging, positive when charging
    """,
    lifespan=lifespan,
)

# CORS configuration for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Development only - restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health_router)
app.include_router(vehicle_router)
app.include_router(telemetry_router)
app.include_router(simulation_router)
app.include_router(intelligence_router)
app.include_router(ai_router)


@app.get("/", include_in_schema=False)
async def root():
    """Root endpoint redirecting to docs."""
    return {
        "message": f"Welcome to {settings.APP_NAME}",
        "version": settings.APP_VERSION,
        "docs": "/docs",
        "notice": "All telemetry is SYNTHETIC SIMULATED DATA",
    }
