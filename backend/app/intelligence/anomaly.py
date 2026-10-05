"""Anomaly detection service.

This module detects energy consumption anomalies by comparing
observed driving against baseline using a weighted formula.
"""

from dataclasses import dataclass
from enum import Enum
from typing import List, Optional

from app.intelligence.config import IntelligenceConfig, DEFAULT_CONFIG
from app.intelligence.features import TelemetryFeatures


class AnomalySeverity(str, Enum):
    """Severity of detected anomaly."""

    NORMAL = "NORMAL"  # 0-24
    LOW = "LOW"  # 25-49
    MEDIUM = "MEDIUM"  # 50-74
    HIGH = "HIGH"  # 75-89
    CRITICAL = "CRITICAL"  # 90-100


@dataclass
class AnomalyComponent:
    """Individual component of anomaly score."""

    name: str
    observed_value: Optional[float]
    baseline_value: Optional[float]
    deviation_ratio: float  # 0-1
    weighted_contribution: float  # After applying weight
    weight: float
    description: str


@dataclass
class AnomalyDetectionResult:
    """Result of anomaly detection."""

    anomaly_score: float  # 0-100
    severity: AnomalySeverity
    is_anomalous: bool
    reasons: List[str]
    components: List[AnomalyComponent]
    baseline_available: bool
    confidence: str


class AnomalyDetector:
    """Detects energy consumption anomalies.

    LOCKED ANOMALY FORMULA:
        For each component:
            deviation_ratio = abs(observed - baseline) / max(abs(baseline), epsilon)
            Clamped to [0, 1]

        Then:
            anomaly_score = clamp(
                100 * (
                    0.60 * energy_deviation_ratio +
                    0.20 * speed_deviation_ratio +
                    0.10 * acceleration_deviation_ratio +
                    0.10 * temperature_deviation_ratio
                ),
                0, 100
            )

    Severity thresholds:
        0-24: NORMAL
        25-49: LOW
        50-74: MEDIUM
        75-89: HIGH
        90-100: CRITICAL

    For ENERGY_ANOMALY scenario:
        energy_deviation_ratio reflects the scenario's defined excess consumption
        (e.g., 20% excess = 0.20)
    """

    def __init__(self, config: IntelligenceConfig = DEFAULT_CONFIG):
        """Initialize anomaly detector.

        Args:
            config: Intelligence configuration
        """
        self.config = config

    def detect(
        self,
        observed_features: TelemetryFeatures,
        baseline_features: Optional[TelemetryFeatures] = None,
    ) -> AnomalyDetectionResult:
        """Detect anomalies by comparing observed vs baseline.

        Args:
            observed_features: Features from observed driving
            baseline_features: Features from baseline driving (optional)

        Returns:
            AnomalyDetectionResult with anomaly score and details
        """
        if baseline_features is None:
            return self._unavailable_result()

        # Calculate each component
        components = []

        # Energy component (weight: 0.60)
        energy_component = self._calculate_component(
            "energy",
            observed_features.efficiency_kwh_per_100km,
            baseline_features.efficiency_kwh_per_100km,
            self.config.anomaly_weight_energy,
        )
        components.append(energy_component)

        # Speed component (weight: 0.20)
        speed_component = self._calculate_component(
            "speed",
            observed_features.average_speed_kmh,
            baseline_features.average_speed_kmh,
            self.config.anomaly_weight_speed,
        )
        components.append(speed_component)

        # Acceleration component (weight: 0.10)
        accel_component = self._calculate_component(
            "acceleration",
            observed_features.average_acceleration_mps2,
            baseline_features.average_acceleration_mps2,
            self.config.anomaly_weight_acceleration,
        )
        components.append(accel_component)

        # Temperature component (weight: 0.10)
        temp_component = self._calculate_component(
            "temperature",
            observed_features.battery_temperature_average_c,
            baseline_features.battery_temperature_average_c,
            self.config.anomaly_weight_temperature,
        )
        components.append(temp_component)

        # Calculate total anomaly score
        total_weighted = sum(c.weighted_contribution for c in components)
        anomaly_score = max(0.0, min(100.0, total_weighted * 100))

        # Determine severity
        severity = self._determine_severity(anomaly_score)
        is_anomalous = anomaly_score >= self.config.anomaly_threshold_low

        # Generate reasons
        reasons = self._generate_reasons(components, anomaly_score)

        # Determine confidence
        confidence = self._determine_confidence(observed_features, baseline_features)

        return AnomalyDetectionResult(
            anomaly_score=round(anomaly_score, self.config.score_precision),
            severity=severity,
            is_anomalous=is_anomalous,
            reasons=reasons,
            components=components,
            baseline_available=True,
            confidence=confidence,
        )

    def _calculate_component(
        self,
        name: str,
        observed_value: Optional[float],
        baseline_value: Optional[float],
        weight: float,
    ) -> AnomalyComponent:
        """Calculate a single anomaly component.

        Args:
            name: Component name
            observed_value: Observed metric value
            baseline_value: Baseline metric value
            weight: Weight for this component

        Returns:
            AnomalyComponent with deviation and contribution
        """
        if observed_value is None or baseline_value is None:
            return AnomalyComponent(
                name=name,
                observed_value=observed_value,
                baseline_value=baseline_value,
                deviation_ratio=0.0,
                weighted_contribution=0.0,
                weight=weight,
                description=f"{name} data unavailable for comparison",
            )

        # Calculate deviation ratio
        baseline_abs = max(abs(baseline_value), self.config.epsilon)
        deviation = abs(observed_value - baseline_value)
        deviation_ratio = min(deviation / baseline_abs, 1.0)

        # Calculate weighted contribution
        weighted_contribution = weight * deviation_ratio

        # Generate description
        if deviation_ratio < 0.1:
            desc = f"{name} within normal range"
        elif deviation_ratio < 0.3:
            desc = f"{name} slightly elevated"
        elif deviation_ratio < 0.6:
            desc = f"{name} moderately elevated"
        else:
            desc = f"{name} significantly elevated"

        return AnomalyComponent(
            name=name,
            observed_value=round(observed_value, self.config.score_precision),
            baseline_value=round(baseline_value, self.config.score_precision),
            deviation_ratio=round(deviation_ratio, 4),
            weighted_contribution=round(weighted_contribution, 4),
            weight=weight,
            description=desc,
        )

    def _determine_severity(self, score: float) -> AnomalySeverity:
        """Determine anomaly severity from score.

        Args:
            score: Anomaly score (0-100)

        Returns:
            AnomalySeverity enum
        """
        if score < self.config.anomaly_threshold_low:
            return AnomalySeverity.NORMAL
        elif score < self.config.anomaly_threshold_medium:
            return AnomalySeverity.LOW
        elif score < self.config.anomaly_threshold_high:
            return AnomalySeverity.MEDIUM
        elif score < self.config.anomaly_threshold_critical:
            return AnomalySeverity.HIGH
        else:
            return AnomalySeverity.CRITICAL

    def _generate_reasons(
        self, components: List[AnomalyComponent], total_score: float
    ) -> List[str]:
        """Generate human-readable reasons for anomaly.

        Args:
            components: List of anomaly components
            total_score: Total anomaly score

        Returns:
            List of reason strings
        """
        reasons = []

        if total_score < self.config.anomaly_threshold_low:
            reasons.append("No significant anomaly detected")
            return reasons

        # Sort components by contribution
        sorted_components = sorted(
            components, key=lambda c: c.weighted_contribution, reverse=True
        )

        # Add reasons for top contributors
        for comp in sorted_components:
            if comp.weighted_contribution > 0.05:  # Significant contribution
                if comp.deviation_ratio > 0.2:
                    reasons.append(
                        f"{comp.name.capitalize()} deviation: "
                        f"{comp.deviation_ratio * 100:.1f}% from baseline"
                    )

        if not reasons:
            reasons.append(f"Cumulative deviation from baseline: {total_score:.1f}")

        return reasons

    def _determine_confidence(
        self, observed: TelemetryFeatures, baseline: TelemetryFeatures
    ) -> str:
        """Determine confidence level of anomaly detection.

        Args:
            observed: Observed features
            baseline: Baseline features

        Returns:
            Confidence description string
        """
        if (
            observed.sample_count >= self.config.min_telemetry_samples_for_high_confidence
            and baseline.sample_count >= self.config.min_telemetry_samples_for_high_confidence
            and observed.distance_km >= self.config.min_distance_for_high_confidence_km
        ):
            return "HIGH - sufficient data for reliable detection"
        elif (
            observed.sample_count >= self.config.min_telemetry_samples_for_medium_confidence
            and baseline.sample_count >= self.config.min_telemetry_samples_for_medium_confidence
        ):
            return "MEDIUM - limited data, detection may vary"
        else:
            return "LOW - insufficient data for reliable detection"

    def _unavailable_result(self) -> AnomalyDetectionResult:
        """Return result when baseline is unavailable."""
        return AnomalyDetectionResult(
            anomaly_score=0.0,
            severity=AnomalySeverity.NORMAL,
            is_anomalous=False,
            reasons=["Baseline unavailable - anomaly detection not possible"],
            components=[],
            baseline_available=False,
            confidence="LOW - no baseline for comparison",
        )
