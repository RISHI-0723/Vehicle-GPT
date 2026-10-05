"""Vehicle API endpoints."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.services.vehicle_service import VehicleService
from app.schemas.vehicle import (
    VehicleResponse,
    VehicleListResponse,
    VehicleStateResponse,
)


router = APIRouter(prefix="/api/v1/vehicles", tags=["Vehicles"])


@router.get("", response_model=VehicleListResponse)
async def list_vehicles(db: Session = Depends(get_db)):
    """List all vehicles.

    Returns a list of all registered vehicles with their canonical configuration.
    """
    service = VehicleService(db)
    vehicles = service.get_all_vehicles()

    return VehicleListResponse(
        vehicles=[VehicleResponse.model_validate(v) for v in vehicles],
        count=len(vehicles),
    )


@router.get("/{vehicle_id}", response_model=VehicleResponse)
async def get_vehicle(vehicle_id: str, db: Session = Depends(get_db)):
    """Get a specific vehicle by ID.

    Returns the canonical configuration for the requested vehicle.
    """
    service = VehicleService(db)
    vehicle = service.get_vehicle(vehicle_id)

    if not vehicle:
        raise HTTPException(
            status_code=404,
            detail=f"Vehicle {vehicle_id} not found",
        )

    return VehicleResponse.model_validate(vehicle)


@router.get("/{vehicle_id}/state", response_model=VehicleStateResponse)
async def get_vehicle_state(vehicle_id: str, db: Session = Depends(get_db)):
    """Get current runtime state of a vehicle.

    If telemetry exists, returns the latest simulated state.
    If no telemetry exists, returns the canonical baseline state.
    The timestamp field is None when returning baseline state.
    """
    service = VehicleService(db)
    state = service.get_vehicle_state(vehicle_id)

    if not state:
        raise HTTPException(
            status_code=404,
            detail=f"Vehicle {vehicle_id} not found",
        )

    return state
