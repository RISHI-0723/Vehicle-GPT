"""Simulation API endpoints."""
import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.services.telemetry_service import TelemetryService
from app.schemas.simulation import (
    SimulationRequest,
    SimulationResponse,
    SimulationResetRequest,
    SimulationResetResponse,
    ScenarioInfo,
    ScenarioListResponse,
    ScenarioName,
)
from app.simulator.scenarios import SCENARIO_DESCRIPTIONS, ScenarioType


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/simulation", tags=["Simulation"])


@router.post("/run", response_model=SimulationResponse)
async def run_simulation(
    request: SimulationRequest,
    db: Session = Depends(get_db),
):
    """Run a simulation for a vehicle.

    Generates synthetic telemetry data based on the specified scenario.
    All telemetry is SIMULATED DATA, not real vehicle data.

    **Modes:**
    - **fresh**: Starts from canonical vehicle baseline. Telemetry history is ignored.
    - **continue**: Starts from latest stored telemetry state. simulation_start_time is ignored.

    **Scenarios:**
    - NORMAL_DRIVING: Moderate temperature and smooth everyday driving
    - HOT_INDIAN_DAY: Hot ambient conditions with increased thermal load
    - AGGRESSIVE_DRIVING: Frequent acceleration and harsh braking
    - FAST_CHARGING: Stationary high-power charging
    - ENERGY_ANOMALY: Normal driving followed by controlled energy anomaly

    **Determinism:**
    Given identical inputs (vehicle, scenario, duration, interval, seed, mode, state),
    the generated telemetry is identical.
    """
    service = TelemetryService(db)

    try:
        result = service.run_simulation(request)
        return result
    except ValueError as e:
        # Vehicle not found or invalid parameters
        raise HTTPException(status_code=404, detail=str(e))
    except RuntimeError as e:
        # Concurrent simulation conflict
        raise HTTPException(status_code=409, detail=str(e))
    except Exception as e:
        logger.error(f"Simulation failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Simulation failed due to internal error",
        )


@router.post("/reset", response_model=SimulationResetResponse)
async def reset_simulation(
    request: SimulationResetRequest = SimulationResetRequest(),
    db: Session = Depends(get_db),
):
    """Reset simulation data for a vehicle.

    Deletes all telemetry and simulation history for the specified vehicle.
    The vehicle record itself is preserved.
    After reset, runtime state returns to the canonical baseline.

    If vehicle_id is omitted, defaults to VG-DEMO-001.
    """
    service = TelemetryService(db)

    try:
        result = service.reset_vehicle(request.vehicle_id)
        logger.info(f"Reset completed for vehicle {request.vehicle_id}")
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/scenarios", response_model=ScenarioListResponse)
async def list_scenarios():
    """List available simulation scenarios.

    Returns all supported scenarios with their descriptions.
    """
    scenarios = [
        ScenarioInfo(name=scenario.value, description=SCENARIO_DESCRIPTIONS[scenario])
        for scenario in ScenarioType
    ]

    return ScenarioListResponse(scenarios=scenarios)
