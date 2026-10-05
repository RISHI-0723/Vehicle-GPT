"""Intelligence orchestrator for composite analysis.

This module provides the main composite endpoint that orchestrates
all intelligence components for the "Why did my range drop?" flow.

IMPORTANT: This endpoint is SIDE-EFFECT FREE.
- It does NOT generate or persist simulations
- It does NOT mutate telemetry
- It only reads existing data and performs analysis
"""

from dataclasses import dataclass
from typing import Optional, List

from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.db.models import Simulation, Telemetry, Vehicle
from app.intelligence.config import IntelligenceConfig, DEFAULT_CONFIG
from app.intelligence.features import FeatureExtractor, TelemetryFeatures
from app.intelligence.baseline import BaselineSelector, BaselineResult, BaselineMatchType
from app.intelligence.energy import EnergyAnalyzer, EnergyAnalysisResult
from app.intelligence.range_estimator import RangeEstimator, RangeEstimationResult, ConfidenceLevel
from app.intelligence.contributors import ContributorAnalyzer, ContributorAnalysisResult
from app.intelligence.anomaly import AnomalyDetector, AnomalyDetectionResult
from app.intelligence.battery_stress import BatteryStressAnalyzer, BatteryStressResult
from app.intelligence.recommendations import RecommendationEngine, RecommendationResult
from app.intelligence.explanation import ExplanationBuilder, Explanation


@dataclass
class IntelligenceSummary:
    """Summary of all intelligence analysis."""

    # Metadata
    vehicle_id: str
    observed_simulation_id: str
    observed_scenario: str
    baseline_simulation_id: Optional[str]
    baseline_match_type: BaselineMatchType

    # Analysis results
    energy: EnergyAnalysisResult
    range_estimate: RangeEstimationResult
    contributors: ContributorAnalysisResult
    anomaly: AnomalyDetectionResult
    battery_stress: BatteryStressResult
    recommendations: RecommendationResult
    explanation: Explanation

    # Overall confidence
    confidence: ConfidenceLevel


class IntelligenceOrchestrator:
    """Orchestrates all intelligence components.

    This is the main entry point for composite analysis.
    It coordinates:
    1. Analysis target selection
    2. Baseline selection
    3. Feature extraction
    4. Energy analysis
    5. Range estimation
    6. Contributor analysis
    7. Anomaly analysis
    8. Battery stress
    9. Recommendations
    10. Explanation

    IMPORTANT: This is SIDE-EFFECT FREE.
    It does NOT generate simulations, persist telemetry, or modify state.
    """

    # Scenarios suitable for driving analysis
    DRIVING_SCENARIOS = {"NORMAL_DRIVING", "HOT_INDIAN_DAY", "AGGRESSIVE_DRIVING", "ENERGY_ANOMALY"}

    def __init__(self, db: Session, config: IntelligenceConfig = DEFAULT_CONFIG):
        """Initialize orchestrator.

        Args:
            db: Database session
            config: Intelligence configuration
        """
        self.db = db
        self.config = config

        # Initialize all analyzers
        self.feature_extractor = FeatureExtractor(config)
        self.baseline_selector = BaselineSelector(db)
        self.energy_analyzer = EnergyAnalyzer(config)
        self.range_estimator = RangeEstimator(config)
        self.contributor_analyzer = ContributorAnalyzer(config)
        self.anomaly_detector = AnomalyDetector(config)
        self.stress_analyzer = BatteryStressAnalyzer(config)
        self.recommendation_engine = RecommendationEngine(config)
        self.explanation_builder = ExplanationBuilder(config)

    def analyze_why_range_dropped(
        self,
        vehicle_id: str,
        simulation_id: Optional[str] = None,
    ) -> IntelligenceSummary:
        """Main "Why did my range drop?" analysis.

        Args:
            vehicle_id: Vehicle to analyze
            simulation_id: Specific simulation (optional, defaults to latest)

        Returns:
            IntelligenceSummary with all analysis results

        Raises:
            ValueError: If vehicle or suitable simulation not found
        """
        # Verify vehicle exists
        vehicle = self.db.query(Vehicle).filter(Vehicle.vehicle_id == vehicle_id).first()
        if not vehicle:
            raise ValueError(f"Vehicle not found: {vehicle_id}")

        # Get observed simulation
        if simulation_id:
            observed_sim = (
                self.db.query(Simulation)
                .filter(Simulation.simulation_id == simulation_id)
                .first()
            )
            if not observed_sim:
                raise ValueError(f"Simulation not found: {simulation_id}")
        else:
            # Find latest suitable driving simulation
            observed_sim = self._find_latest_driving_simulation(vehicle_id)
            if not observed_sim:
                raise ValueError(f"No suitable driving simulation found for vehicle: {vehicle_id}")

        # Get observed telemetry
        observed_telemetry = self._get_simulation_telemetry(observed_sim.simulation_id)
        if not observed_telemetry:
            raise ValueError(f"No telemetry found for simulation: {observed_sim.simulation_id}")

        # Extract observed features
        observed_features = self.feature_extractor.extract(observed_telemetry)

        # Get baseline
        baseline_result = self.baseline_selector.select_baseline(
            vehicle_id,
            observed_sim.duration_minutes,
            observed_sim.interval_seconds,
        )

        # Extract baseline features if available
        baseline_features: Optional[TelemetryFeatures] = None
        if baseline_result.is_available and baseline_result.telemetry:
            baseline_features = self.feature_extractor.extract(baseline_result.telemetry)

        # Run all analyses
        energy_result = self.energy_analyzer.analyze(observed_features, baseline_features)

        range_result = self.range_estimator.estimate(
            current_soc_percent=observed_features.ending_soc_percent,
            observed_features=observed_features,
            baseline_features=baseline_features,
        )

        contributor_result = self.contributor_analyzer.analyze(observed_features, baseline_features)

        anomaly_result = self.anomaly_detector.detect(observed_features, baseline_features)

        stress_result = self.stress_analyzer.analyze(observed_features)

        recommendation_result = self.recommendation_engine.generate(
            features=observed_features,
            anomaly_result=anomaly_result,
            stress_result=stress_result,
            contributor_result=contributor_result,
        )

        # Build explanation
        explanation = self.explanation_builder.build_why_range_explanation(
            energy_result=energy_result,
            range_result=range_result,
            contributor_result=contributor_result,
            anomaly_result=anomaly_result,
            stress_result=stress_result,
            recommendation_result=recommendation_result,
            baseline_available=baseline_result.is_available,
        )

        # Determine overall confidence
        confidence = self._determine_overall_confidence(
            observed_features, baseline_features, baseline_result
        )

        return IntelligenceSummary(
            vehicle_id=vehicle_id,
            observed_simulation_id=observed_sim.simulation_id,
            observed_scenario=observed_sim.scenario,
            baseline_simulation_id=baseline_result.simulation_id,
            baseline_match_type=baseline_result.match_type,
            energy=energy_result,
            range_estimate=range_result,
            contributors=contributor_result,
            anomaly=anomaly_result,
            battery_stress=stress_result,
            recommendations=recommendation_result,
            explanation=explanation,
            confidence=confidence,
        )

    def get_summary(
        self,
        vehicle_id: str,
        simulation_id: Optional[str] = None,
    ) -> IntelligenceSummary:
        """Get a complete intelligence summary.

        This is essentially the same as analyze_why_range_dropped,
        providing a summary endpoint.

        Args:
            vehicle_id: Vehicle to analyze
            simulation_id: Specific simulation (optional)

        Returns:
            IntelligenceSummary
        """
        return self.analyze_why_range_dropped(vehicle_id, simulation_id)

    def _find_latest_driving_simulation(self, vehicle_id: str) -> Optional[Simulation]:
        """Find the latest suitable driving simulation.

        Args:
            vehicle_id: Vehicle to find simulation for

        Returns:
            Latest driving simulation or None
        """
        return (
            self.db.query(Simulation)
            .filter(Simulation.vehicle_id == vehicle_id)
            .filter(Simulation.scenario.in_(self.DRIVING_SCENARIOS))
            .order_by(desc(Simulation.created_at))
            .first()
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

    def _determine_overall_confidence(
        self,
        observed_features: TelemetryFeatures,
        baseline_features: Optional[TelemetryFeatures],
        baseline_result: BaselineResult,
    ) -> ConfidenceLevel:
        """Determine overall confidence level.

        Args:
            observed_features: Observed telemetry features
            baseline_features: Baseline telemetry features (may be None)
            baseline_result: Baseline selection result

        Returns:
            ConfidenceLevel enum
        """
        # No baseline = low confidence
        if not baseline_result.is_available:
            return ConfidenceLevel.LOW

        # Insufficient observed data
        if observed_features.sample_count < self.config.min_telemetry_samples_for_medium_confidence:
            return ConfidenceLevel.LOW

        # Check for high confidence
        if (
            observed_features.sample_count >= self.config.min_telemetry_samples_for_high_confidence
            and observed_features.distance_km >= self.config.min_distance_for_high_confidence_km
            and baseline_result.match_type == BaselineMatchType.EXACT
        ):
            return ConfidenceLevel.HIGH

        return ConfidenceLevel.MEDIUM
