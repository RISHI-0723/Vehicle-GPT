"""Contributor analysis service.

This module analyzes which factors contributed to differences
between observed driving and baseline.
"""

from dataclasses import dataclass
from enum import Enum
from typing import List, Optional

from app.intelligence.config import IntelligenceConfig, DEFAULT_CONFIG
from app.intelligence.features import TelemetryFeatures


class ImpactLevel(str, Enum):
    """Impact level of a contributor."""

    LOW = "LOW"  # 0.00 - 0.24
    MEDIUM = "MEDIUM"  # 0.25 - 0.49
    HIGH = "HIGH"  # 0.50 - 0.74
    CRITICAL = "CRITICAL"  # 0.75 - 1.00
    UNAVAILABLE = "UNAVAILABLE"  # Cannot calculate


@dataclass
class Contributor:
    """A single contributor to the analysis."""

    id: str
    name: str
    observed_value: Optional[float]
    baseline_value: Optional[float]
    difference: Optional[float]
    difference_percent: Optional[float]
    impact_score: float  # 0-100 scale
    impact_level: ImpactLevel
    description: str
    is_available: bool = True


@dataclass
class ContributorAnalysisResult:
    """Result of contributor analysis."""

    contributors: List[Contributor]
    total_contributors: int
    available_contributors: int
    baseline_available: bool
    summary: str


class ContributorAnalyzer:
    """Analyzes factors contributing to efficiency differences.

    Calculates impact scores for various driving factors by comparing
    observed values against baseline. Uses a normalized deviation formula.

    Formula:
        raw_deviation = abs(observed - baseline) / max(abs(baseline), epsilon)
        impact_score = clamp(raw_deviation, 0, 1) * 100

    Impact levels:
        0-24: LOW
        25-49: MEDIUM
        50-74: HIGH
        75-100: CRITICAL
    """

    CONTRIBUTOR_DEFINITIONS = [
        {
            "id": "speed",
            "name": "Average Speed",
            "feature_key": "average_speed_kmh",
            "unit": "km/h",
            "description_template": "Average speed was {observed:.1f} km/h vs baseline {baseline:.1f} km/h",
        },
        {
            "id": "max_speed",
            "name": "Maximum Speed",
            "feature_key": "max_speed_kmh",
            "unit": "km/h",
            "description_template": "Maximum speed was {observed:.1f} km/h vs baseline {baseline:.1f} km/h",
        },
        {
            "id": "acceleration",
            "name": "Average Acceleration",
            "feature_key": "average_acceleration_mps2",
            "unit": "m/s\u00b2",
            "description_template": "Acceleration was {observed:.2f} m/s\u00b2 vs baseline {baseline:.2f} m/s\u00b2",
        },
        {
            "id": "max_acceleration",
            "name": "Peak Acceleration",
            "feature_key": "max_acceleration_mps2",
            "unit": "m/s\u00b2",
            "description_template": "Peak acceleration was {observed:.2f} m/s\u00b2 vs baseline {baseline:.2f} m/s\u00b2",
        },
        {
            "id": "battery_temperature",
            "name": "Battery Temperature",
            "feature_key": "battery_temperature_average_c",
            "unit": "\u00b0C",
            "description_template": "Battery temperature averaged {observed:.1f}\u00b0C vs baseline {baseline:.1f}\u00b0C",
        },
        {
            "id": "battery_power",
            "name": "Average Power Draw",
            "feature_key": "battery_power_average_kw",
            "unit": "kW",
            "description_template": "Power draw averaged {observed:.1f} kW vs baseline {baseline:.1f} kW",
        },
        {
            "id": "regen",
            "name": "Regeneration Ratio",
            "feature_key": "regen_ratio",
            "unit": "",
            "description_template": "Regen ratio was {observed:.2f} vs baseline {baseline:.2f}",
        },
        {
            "id": "aggressive_driving",
            "name": "Aggressive Driving Score",
            "feature_key": "aggressive_driving_score_average",
            "unit": "",
            "description_template": "Aggressive driving score was {observed:.1f} vs baseline {baseline:.1f}",
        },
        {
            "id": "ambient_temperature",
            "name": "Ambient Temperature",
            "feature_key": "ambient_temperature_average_c",
            "unit": "\u00b0C",
            "description_template": "Ambient temperature averaged {observed:.1f}\u00b0C vs baseline {baseline:.1f}\u00b0C",
        },
    ]

    def __init__(self, config: IntelligenceConfig = DEFAULT_CONFIG):
        """Initialize contributor analyzer.

        Args:
            config: Intelligence configuration
        """
        self.config = config

    def analyze(
        self,
        observed_features: TelemetryFeatures,
        baseline_features: Optional[TelemetryFeatures] = None,
    ) -> ContributorAnalysisResult:
        """Analyze contributors to efficiency differences.

        Args:
            observed_features: Features from observed driving
            baseline_features: Features from baseline driving (optional)

        Returns:
            ContributorAnalysisResult with all contributors
        """
        contributors = []
        available_count = 0

        for defn in self.CONTRIBUTOR_DEFINITIONS:
            contributor = self._calculate_contributor(
                defn, observed_features, baseline_features
            )
            contributors.append(contributor)
            if contributor.is_available:
                available_count += 1

        # Sort by impact score descending
        contributors.sort(key=lambda c: c.impact_score, reverse=True)

        # Generate summary
        summary = self._generate_summary(contributors, baseline_features is not None)

        return ContributorAnalysisResult(
            contributors=contributors,
            total_contributors=len(contributors),
            available_contributors=available_count,
            baseline_available=baseline_features is not None,
            summary=summary,
        )

    def _calculate_contributor(
        self,
        definition: dict,
        observed: TelemetryFeatures,
        baseline: Optional[TelemetryFeatures],
    ) -> Contributor:
        """Calculate a single contributor.

        Args:
            definition: Contributor definition dict
            observed: Observed features
            baseline: Baseline features (optional)

        Returns:
            Contributor with calculated values
        """
        feature_key = definition["feature_key"]
        observed_value = getattr(observed, feature_key, None)

        if baseline is None:
            # No baseline - contributor unavailable for comparison
            return Contributor(
                id=definition["id"],
                name=definition["name"],
                observed_value=observed_value,
                baseline_value=None,
                difference=None,
                difference_percent=None,
                impact_score=0.0,
                impact_level=ImpactLevel.UNAVAILABLE,
                description="Baseline unavailable for comparison",
                is_available=False,
            )

        baseline_value = getattr(baseline, feature_key, None)

        if observed_value is None or baseline_value is None:
            return Contributor(
                id=definition["id"],
                name=definition["name"],
                observed_value=observed_value,
                baseline_value=baseline_value,
                difference=None,
                difference_percent=None,
                impact_score=0.0,
                impact_level=ImpactLevel.UNAVAILABLE,
                description="Value unavailable for calculation",
                is_available=False,
            )

        # Calculate deviation
        difference = observed_value - baseline_value
        baseline_abs = abs(baseline_value)

        if baseline_abs > self.config.epsilon:
            difference_percent = (difference / baseline_abs) * 100
            raw_deviation = abs(difference) / baseline_abs
        else:
            # Baseline is near zero - use observed as deviation if significant
            if abs(observed_value) > self.config.epsilon:
                difference_percent = 100.0 if difference > 0 else -100.0
                raw_deviation = 1.0
            else:
                difference_percent = 0.0
                raw_deviation = 0.0

        # Clamp and scale impact score to 0-100
        impact_score = min(max(raw_deviation, 0.0), 1.0) * 100

        # Determine impact level
        impact_level = self._determine_impact_level(impact_score / 100)

        # Generate description
        description = definition["description_template"].format(
            observed=observed_value, baseline=baseline_value
        )

        return Contributor(
            id=definition["id"],
            name=definition["name"],
            observed_value=round(observed_value, self.config.score_precision),
            baseline_value=round(baseline_value, self.config.score_precision),
            difference=round(difference, self.config.score_precision),
            difference_percent=round(difference_percent, self.config.percentage_precision),
            impact_score=round(impact_score, self.config.score_precision),
            impact_level=impact_level,
            description=description,
            is_available=True,
        )

    def _determine_impact_level(self, normalized_score: float) -> ImpactLevel:
        """Determine impact level from normalized score (0-1).

        Args:
            normalized_score: Score between 0 and 1

        Returns:
            ImpactLevel enum
        """
        if normalized_score <= self.config.contributor_impact_low_max:
            return ImpactLevel.LOW
        elif normalized_score <= self.config.contributor_impact_medium_max:
            return ImpactLevel.MEDIUM
        elif normalized_score <= self.config.contributor_impact_high_max:
            return ImpactLevel.HIGH
        else:
            return ImpactLevel.CRITICAL

    def _generate_summary(self, contributors: List[Contributor], baseline_available: bool) -> str:
        """Generate summary of contributor analysis.

        Args:
            contributors: List of analyzed contributors
            baseline_available: Whether baseline was available

        Returns:
            Summary string
        """
        if not baseline_available:
            return "Baseline unavailable - contributor analysis limited to observed values only."

        # Count contributors by impact level
        high_impact = [c for c in contributors if c.impact_level in (ImpactLevel.HIGH, ImpactLevel.CRITICAL)]
        medium_impact = [c for c in contributors if c.impact_level == ImpactLevel.MEDIUM]

        if high_impact:
            names = ", ".join(c.name for c in high_impact[:3])
            return f"High-impact contributors: {names}"
        elif medium_impact:
            names = ", ".join(c.name for c in medium_impact[:3])
            return f"Moderate contributors: {names}"
        else:
            return "All factors within normal range compared to baseline."
