"""API routes module."""
from .routes_health import router as health_router
from .routes_vehicle import router as vehicle_router
from .routes_telemetry import router as telemetry_router
from .routes_simulation import router as simulation_router
from .routes_intelligence import router as intelligence_router
from .routes_ai import router as ai_router

__all__ = [
    "health_router",
    "vehicle_router",
    "telemetry_router",
    "simulation_router",
    "intelligence_router",
    "ai_router",
]
