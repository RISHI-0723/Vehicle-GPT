"""Explanation builder for intelligence analysis.

This module transforms structured intelligence outputs into
human-readable explanations using deterministic templates.

NOTE: This does NOT use LLM or random text generation.
All explanations are template-based and deterministic.
"""

from dataclasses import dataclass
from typing import List, Optional

from app.intelligence.config import IntelligenceConfig, DEFAULT_CONFIG
from app.intelligence.energy import EnergyAnalysisResult, EfficiencyRating
from app.intelligence.range_estimator import RangeEstimationResult, ConfidenceLevel
from app.intelligence.anomaly import AnomalyDetectionResult, AnomalySeverity
from app.intelligence.contributors import ContributorAnalysisResult, ImpactLevel
from app.intelligence.battery_stress import BatteryStressResult, StressLevel
from app.intelligence.recommendations import RecommendationResult


@dataclass
class Explanation:
    """Human-readable explanation of intelligence analysis."""

    headline: str
    summary: str
    key_factors: List[str]
    recommendation_summary: str
    confidence: str


class ExplanationBuilder:
    """Builds human-readable explanations from intelligence outputs.

    All explanations are template-based and deterministic.
    No LLM or random text generation is used.
    """

    def __init__(self, config: IntelligenceConfig = DEFAULT_CONFIG):
        """Initialize explanation builder.

        Args:
            config: Intelligence configuration
        """
        self.config = config

    def build(
        self,
        energy_result: Optional[EnergyAnalysisResult] = None,
        range_result: Optional[RangeEstimationResult] = None,
        anomaly_result: Optional[AnomalyDetectionResult] = None,
        contributor_result: Optional[ContributorAnalysisResult] = None,
        stress_result: Optional[BatteryStressResult] = None,
        recommendation_result: Optional[RecommendationResult] = None,
        baseline_available: bool = False,
    ) -> Explanation:
        """Build explanation from intelligence outputs.

        Args:
            energy_result: Energy analysis result
            range_result: Range estimation result
            anomaly_result: Anomaly detection result
            contributor_result: Contributor analysis result
            stress_result: Battery stress result
            recommendation_result: Recommendation result
            baseline_available: Whether baseline was available

        Returns:
            Explanation with human-readable text
        """
        # Build headline
        headline = self._build_headline(
            energy_result, anomaly_result, baseline_available
        )

        # Build summary
        summary = self._build_summary(
            energy_result, range_result, anomaly_result, baseline_available
        )

        # Build key factors
        key_factors = self._build_key_factors(
            contributor_result, stress_result, anomaly_result
        )

        # Build recommendation summary
        recommendation_summary = self._build_recommendation_summary(
            recommendation_result
        )

        # Determine overall confidence
        confidence = self._determine_confidence(
            energy_result, range_result, anomaly_result, baseline_available
        )

        return Explanation(
            headline=headline,
            summary=summary,
            key_factors=key_factors,
            recommendation_summary=recommendation_summary,
            confidence=confidence,
        )

    def _build_headline(
        self,
        energy_result: Optional[EnergyAnalysisResult],
        anomaly_result: Optional[AnomalyDetectionResult],
        baseline_available: bool,
    ) -> str:
        """Build the headline explanation.

        Args:
            energy_result: Energy analysis result
            anomaly_result: Anomaly detection result
            baseline_available: Whether baseline was available

        Returns:
            Headline string
        """
        if not baseline_available:
            return "Analysis completed without baseline comparison"

        # Check for anomaly first
        if anomaly_result is not None and anomaly_result.is_anomalous:
            if anomaly_result.severity in (AnomalySeverity.HIGH, AnomalySeverity.CRITICAL):
                return "Significant energy anomaly detected during this trip"
            else:
                return "Moderate energy deviation from normal driving detected"

        # Check energy efficiency
        if energy_result is not None:
            if energy_result.rating == EfficiencyRating.INEFFICIENT:
                return "Energy consumption was higher than your normal baseline"
            elif energy_result.rating == EfficiencyRating.EFFICIENT:
                return "Energy consumption was better than your normal baseline"
            elif energy_result.rating == EfficiencyRating.NORMAL:
                return "Energy consumption was within normal range"

        return "Driving analysis completed"

    def _build_summary(
        self,
        energy_result: Optional[EnergyAnalysisResult],
        range_result: Optional[RangeEstimationResult],
        anomaly_result: Optional[AnomalyDetectionResult],
        baseline_available: bool,
    ) -> str:
        """Build the summary paragraph.

        Args:
            energy_result: Energy analysis result
            range_result: Range estimation result
            anomaly_result: Anomaly detection result
            baseline_available: Whether baseline was available

        Returns:
            Summary string
        """
        parts = []

        # Energy summary
        if energy_result is not None:
            if energy_result.efficiency_delta_percent is not None:
                delta = energy_result.efficiency_delta_percent
                if abs(delta) < 5:
                    parts.append(
                        f"Efficiency of {energy_result.efficiency_kwh_per_100km:.1f} kWh/100km "
                        f"is similar to your baseline."
                    )
                elif delta > 0:
                    parts.append(
                        f"Efficiency of {energy_result.efficiency_kwh_per_100km:.1f} kWh/100km "
                        f"is {delta:.1f}% worse than your baseline."
                    )
                else:
                    parts.append(
                        f"Efficiency of {energy_result.efficiency_kwh_per_100km:.1f} kWh/100km "
                        f"is {abs(delta):.1f}% better than your baseline."
                    )
            elif energy_result.efficiency_kwh_per_100km is not None:
                parts.append(
                    f"Trip efficiency was {energy_result.efficiency_kwh_per_100km:.1f} kWh/100km."
                )

        # Range summary
        if range_result is not None and range_result.estimated_range_km is not None:
            parts.append(
                f"Estimated remaining range is approximately {range_result.estimated_range_km:.0f} km "
                f"at current SOC of {range_result.current_soc_percent:.0f}%."
            )

        # Anomaly summary
        if anomaly_result is not None and anomaly_result.is_anomalous:
            parts.append(
                f"An energy anomaly was detected with score {anomaly_result.anomaly_score:.0f}/100."
            )

        if not parts:
            if baseline_available:
                return "Analysis completed. No significant deviations from baseline detected."
            else:
                return "Analysis completed. Baseline comparison was not available."

        return " ".join(parts)

    def _build_key_factors(
        self,
        contributor_result: Optional[ContributorAnalysisResult],
        stress_result: Optional[BatteryStressResult],
        anomaly_result: Optional[AnomalyDetectionResult],
    ) -> List[str]:
        """Build list of key contributing factors.

        Args:
            contributor_result: Contributor analysis result
            stress_result: Battery stress result
            anomaly_result: Anomaly detection result

        Returns:
            List of factor strings
        """
        factors = []

        # Top contributors
        if contributor_result is not None and contributor_result.baseline_available:
            high_impact = [
                c for c in contributor_result.contributors
                if c.impact_level in (ImpactLevel.HIGH, ImpactLevel.CRITICAL)
            ]
            for contributor in high_impact[:3]:
                factors.append(contributor.description)

        # Stress factors
        if stress_result is not None:
            if stress_result.stress_level in (StressLevel.ELEVATED, StressLevel.HIGH, StressLevel.CRITICAL):
                # Find top stress component
                top_stress = max(
                    stress_result.components,
                    key=lambda c: c.raw_score,
                    default=None
                )
                if top_stress is not None and top_stress.raw_score > 40:
                    factors.append(f"{top_stress.name} contributed to elevated battery stress")

        # Anomaly components
        if anomaly_result is not None and anomaly_result.is_anomalous:
            for reason in anomaly_result.reasons[:2]:
                if reason not in factors:
                    factors.append(reason)

        return factors[:5]  # Limit to 5 factors

    def _build_recommendation_summary(
        self,
        recommendation_result: Optional[RecommendationResult],
    ) -> str:
        """Build recommendation summary.

        Args:
            recommendation_result: Recommendation result

        Returns:
            Recommendation summary string
        """
        if recommendation_result is None or not recommendation_result.recommendations:
            return "No specific recommendations at this time."

        recs = recommendation_result.recommendations
        if len(recs) == 1:
            return f"Recommendation: {recs[0].title}."
        else:
            titles = [r.title for r in recs[:3]]
            return f"Top recommendations: {'; '.join(titles)}."

    def _determine_confidence(
        self,
        energy_result: Optional[EnergyAnalysisResult],
        range_result: Optional[RangeEstimationResult],
        anomaly_result: Optional[AnomalyDetectionResult],
        baseline_available: bool,
    ) -> str:
        """Determine overall confidence level.

        Args:
            energy_result: Energy analysis result
            range_result: Range estimation result
            anomaly_result: Anomaly detection result
            baseline_available: Whether baseline was available

        Returns:
            Confidence description string
        """
        if not baseline_available:
            return "LOW - baseline comparison not available"

        # Check range confidence
        if range_result is not None:
            if range_result.confidence == ConfidenceLevel.HIGH:
                return "HIGH - sufficient data for reliable analysis"
            elif range_result.confidence == ConfidenceLevel.MEDIUM:
                return "MEDIUM - adequate data, some uncertainty"

        # Check if we have sufficient data
        if energy_result is not None and energy_result.sample_count >= 10:
            return "MEDIUM - adequate data for analysis"

        return "LOW - limited data, results may vary"

    def build_why_range_explanation(
        self,
        energy_result: Optional[EnergyAnalysisResult],
        range_result: Optional[RangeEstimationResult],
        contributor_result: Optional[ContributorAnalysisResult],
        anomaly_result: Optional[AnomalyDetectionResult],
        stress_result: Optional[BatteryStressResult],
        recommendation_result: Optional[RecommendationResult],
        baseline_available: bool,
    ) -> Explanation:
        """Build explanation specifically for "why did my range drop?" query.

        Args:
            All intelligence results

        Returns:
            Explanation focused on range drop reasoning
        """
        # Determine if range actually dropped
        range_dropped = False
        if energy_result is not None and energy_result.rating == EfficiencyRating.INEFFICIENT:
            range_dropped = True
        if anomaly_result is not None and anomaly_result.is_anomalous:
            range_dropped = True

        if range_dropped:
            headline = self._build_range_drop_headline(energy_result, anomaly_result)
        else:
            headline = "No significant range reduction detected"

        # Build comprehensive summary
        summary = self._build_range_summary(
            energy_result, range_result, anomaly_result, baseline_available
        )

        # Key factors - focused on efficiency contributors
        key_factors = self._build_key_factors(
            contributor_result, stress_result, anomaly_result
        )

        # Recommendation summary
        recommendation_summary = self._build_recommendation_summary(recommendation_result)

        # Confidence
        confidence = self._determine_confidence(
            energy_result, range_result, anomaly_result, baseline_available
        )

        return Explanation(
            headline=headline,
            summary=summary,
            key_factors=key_factors,
            recommendation_summary=recommendation_summary,
            confidence=confidence,
        )

    def _build_range_drop_headline(
        self,
        energy_result: Optional[EnergyAnalysisResult],
        anomaly_result: Optional[AnomalyDetectionResult],
    ) -> str:
        """Build headline for range drop explanation."""
        if anomaly_result is not None and anomaly_result.severity in (
            AnomalySeverity.HIGH, AnomalySeverity.CRITICAL
        ):
            return "Significant efficiency drop reduced your estimated range"

        if energy_result is not None and energy_result.efficiency_delta_percent is not None:
            delta = energy_result.efficiency_delta_percent
            if delta > 20:
                return "Energy consumption was significantly higher than baseline"
            elif delta > 10:
                return "Energy consumption was moderately higher than baseline"

        return "Your estimated range dropped due to higher energy consumption"

    def _build_range_summary(
        self,
        energy_result: Optional[EnergyAnalysisResult],
        range_result: Optional[RangeEstimationResult],
        anomaly_result: Optional[AnomalyDetectionResult],
        baseline_available: bool,
    ) -> str:
        """Build summary focused on range explanation."""
        parts = []

        if not baseline_available:
            parts.append(
                "Without a baseline comparison, we cannot determine if this trip's "
                "efficiency differs from your normal driving."
            )
        elif energy_result is not None:
            if energy_result.efficiency_delta_percent is not None:
                delta = energy_result.efficiency_delta_percent
                if delta > 0:
                    parts.append(
                        f"Your energy consumption was {delta:.1f}% higher than your normal "
                        f"baseline ({energy_result.efficiency_kwh_per_100km:.1f} vs "
                        f"{energy_result.baseline_efficiency_kwh_per_100km:.1f} kWh/100km)."
                    )
                elif delta < -5:
                    parts.append(
                        f"Your efficiency was actually {abs(delta):.1f}% better than baseline."
                    )
                else:
                    parts.append("Your efficiency was similar to your baseline.")

        if range_result is not None and range_result.estimated_range_km is not None:
            parts.append(
                f"Based on recent efficiency, estimated range is {range_result.estimated_range_km:.0f} km."
            )

        if not parts:
            return "Analysis completed. Review the key factors for more details."

        return " ".join(parts)
