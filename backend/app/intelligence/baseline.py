"""Baseline selection for intelligence analysis.

This module handles the selection of NORMAL_DRIVING simulations for
baseline comparison. Baseline generation NEVER happens implicitly -
only existing persisted simulations are used.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.db.models import Simulation, Telemetry


class BaselineMatchType(str, Enum):
    """Type of baseline match found."""

    EXACT = "EXACT"  # Duration and interval match exactly
    APPROXIMATE = "APPROXIMATE"  # Best available NORMAL_DRIVING simulation
    UNAVAILABLE = "UNAVAILABLE"  # No suitable NORMAL_DRIVING simulation exists


@dataclass
class BaselineResult:
    """Result of baseline selection."""

    simulation_id: Optional[str]
    match_type: BaselineMatchType
    duration_minutes: Optional[int]
    interval_seconds: Optional[int]
    telemetry: Optional[List[Telemetry]]

    @property
    def is_available(self) -> bool:
        """Check if a baseline is available."""
        return self.match_type != BaselineMatchType.UNAVAILABLE


class BaselineSelector:
    """Selects baseline NORMAL_DRIVING simulations for comparison.

    IMPORTANT CONTRACT:
    - Baseline NEVER generates a simulation implicitly
    - Only existing persisted NORMAL_DRIVING simulations are used
    - Selection is deterministic
    - FAST_CHARGING is NOT a suitable driving baseline
    - ENERGY_ANOMALY is NOT automatically the baseline
    """

    # Scenarios that are NOT suitable as driving baselines
    EXCLUDED_BASELINE_SCENARIOS = {"FAST_CHARGING", "ENERGY_ANOMALY"}

    def __init__(self, db: Session):
        """Initialize baseline selector.

        Args:
            db: SQLAlchemy database session
        """
        self.db = db

    def select_baseline(
        self,
        vehicle_id: str,
        target_duration_minutes: Optional[int] = None,
        target_interval_seconds: Optional[int] = None,
    ) -> BaselineResult:
        """Select a NORMAL_DRIVING baseline for comparison.

        Selection rules:
        1. Find existing NORMAL_DRIVING simulations for the vehicle
        2. If a simulation matches duration/interval: EXACT
        3. Otherwise choose newest suitable simulation: APPROXIMATE
        4. If none exists: UNAVAILABLE

        Args:
            vehicle_id: Vehicle to find baseline for
            target_duration_minutes: Desired duration (optional)
            target_interval_seconds: Desired interval (optional)

        Returns:
            BaselineResult with selected baseline or UNAVAILABLE status
        """
        # Query NORMAL_DRIVING simulations for this vehicle
        query = (
            self.db.query(Simulation)
            .filter(Simulation.vehicle_id == vehicle_id)
            .filter(Simulation.scenario == "NORMAL_DRIVING")
            .order_by(desc(Simulation.created_at))
        )

        normal_driving_sims = query.all()

        if not normal_driving_sims:
            return BaselineResult(
                simulation_id=None,
                match_type=BaselineMatchType.UNAVAILABLE,
                duration_minutes=None,
                interval_seconds=None,
                telemetry=None,
            )

        # Try to find exact match if duration/interval specified
        if target_duration_minutes is not None and target_interval_seconds is not None:
            for sim in normal_driving_sims:
                if (
                    sim.duration_minutes == target_duration_minutes
                    and sim.interval_seconds == target_interval_seconds
                ):
                    telemetry = self._get_simulation_telemetry(sim.simulation_id)
                    return BaselineResult(
                        simulation_id=sim.simulation_id,
                        match_type=BaselineMatchType.EXACT,
                        duration_minutes=sim.duration_minutes,
                        interval_seconds=sim.interval_seconds,
                        telemetry=telemetry,
                    )

        # No exact match - use newest NORMAL_DRIVING simulation
        newest_sim = normal_driving_sims[0]
        telemetry = self._get_simulation_telemetry(newest_sim.simulation_id)

        return BaselineResult(
            simulation_id=newest_sim.simulation_id,
            match_type=BaselineMatchType.APPROXIMATE,
            duration_minutes=newest_sim.duration_minutes,
            interval_seconds=newest_sim.interval_seconds,
            telemetry=telemetry,
        )

    def _get_simulation_telemetry(self, simulation_id: str) -> List[Telemetry]:
        """Get telemetry for a simulation.

        Args:
            simulation_id: Simulation to get telemetry for

        Returns:
            List of telemetry records ordered by timestamp
        """
        return (
            self.db.query(Telemetry)
            .filter(Telemetry.simulation_id == simulation_id)
            .order_by(Telemetry.timestamp)
            .all()
        )

    def is_suitable_driving_scenario(self, scenario: str) -> bool:
        """Check if a scenario is suitable for driving analysis.

        FAST_CHARGING is excluded from driving analysis.
        ENERGY_ANOMALY is valid for analysis but not as baseline.

        Args:
            scenario: Scenario name to check

        Returns:
            True if suitable for driving analysis
        """
        return scenario not in {"FAST_CHARGING"}

    def is_suitable_baseline_scenario(self, scenario: str) -> bool:
        """Check if a scenario is suitable as a baseline.

        Only NORMAL_DRIVING is used as baseline.

        Args:
            scenario: Scenario name to check

        Returns:
            True if suitable as baseline (only NORMAL_DRIVING)
        """
        return scenario == "NORMAL_DRIVING"
