"""Telemetry API endpoints."""
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.services.vehicle_service import VehicleService
from app.services.telemetry_service import TelemetryService
from app.schemas.telemetry import TelemetryResponse, TelemetryListResponse
from app.core.config import settings


router = APIRouter(prefix="/api/v1/vehicles", tags=["Telemetry"])


@router.get("/{vehicle_id}/telemetry", response_model=TelemetryListResponse)
async def get_telemetry(
    vehicle_id: str,
    start_time: Optional[datetime] = Query(
        None,
        description="Filter: start time (inclusive)",
    ),
    end_time: Optional[datetime] = Query(
        None,
        description="Filter: end time (inclusive)",
    ),
    limit: int = Query(
        default=settings.DEFAULT_TELEMETRY_LIMIT,
        ge=1,
        le=settings.MAX_TELEMETRY_LIMIT,
        description="Maximum records to return",
    ),
    offset: int = Query(
        default=0,
        ge=0,
        description="Records to skip",
    ),
    db: Session = Depends(get_db),
):
    """Get telemetry for a vehicle.

    Returns telemetry records ordered newest-first (descending timestamp).
    Supports time filtering and pagination.

    - **start_time**: Filter to records >= this timestamp
    - **end_time**: Filter to records <= this timestamp
    - **limit**: Maximum records to return (1-1000, default 100)
    - **offset**: Records to skip for pagination
    """
    # Verify vehicle exists
    vehicle_service = VehicleService(db)
    vehicle = vehicle_service.get_vehicle(vehicle_id)

    if not vehicle:
        raise HTTPException(
            status_code=404,
            detail=f"Vehicle {vehicle_id} not found",
        )

    telemetry_service = TelemetryService(db)
    telemetry, count = telemetry_service.get_telemetry(
        vehicle_id=vehicle_id,
        start_time=start_time,
        end_time=end_time,
        limit=limit,
        offset=offset,
    )

    return TelemetryListResponse(
        vehicle_id=vehicle_id,
        count=count,
        limit=limit,
        offset=offset,
        items=[TelemetryResponse.model_validate(t) for t in telemetry],
    )
