"""Deterministic EV telemetry simulator module."""
from .physics import EVPhysics
from .scenarios import ScenarioConfig, get_scenario_config, SCENARIO_DESCRIPTIONS
from .engine import SimulationEngine, SimulationResult

__all__ = [
    "EVPhysics",
    "ScenarioConfig",
    "get_scenario_config",
    "SCENARIO_DESCRIPTIONS",
    "SimulationEngine",
    "SimulationResult",
]
