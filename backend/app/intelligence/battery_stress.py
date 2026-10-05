"""Battery stress analysis service.

This module calculates operational battery stress based on
driving conditions and usage patterns.

IMPORTANT: This is NOT battery SOH, degradation prediction,
or remaining battery life. It is an estimated operational
stress indicator for the driving session.
"""

from dataclasses import dataclass
from enum import Enum
from typing import List

from app.intelligence.config import IntelligenceConfig, DEFAULT_CONFIG
from app.intelligence.features import TelemetryFeatures


class StressLevel(str, Enum):
    """Battery stress level."""

    LOW = "LOW"  # 0-24
    MODERATE = "MODERATE"  # 25-49
    ELEVATED = "ELEVATED"  # 50-74
    HIGH = "HIGH"  # 75-89
    CRITICAL = "CRITICAL"  # 90-100


@dataclass
class StressComponent:
    """Individual stress component."""

    name: str
    raw_score: float  # 0-100
    weight: float
    weighted_score: float
    description: str


@dataclass
class BatteryStressResult:
    """Result of battery stress analysis.

    DISCLAIMER: This is estimated operational stress, NOT:
    - Battery degradation prediction
    - Battery SOH calculation
    - Remaining battery life estimate
    - Warranty-related assessment
    """

    battery_stress_score: float  # 0-100
    stress_level: StressLevel
    components: List[StressComponent]
    explanation: str
    c_rate_average: float
    c_rate_max: float
    high_temperature_exposure_percent: float
    disclaimer: str = (
        "This is an estimated operational stress indicator based on driving conditions. "
        "It is NOT a battery degradation prediction, SOH calculation, or warranty assessment."
    )


class BatteryStressAnalyzer:
    """Analyzes operational battery stress.

    LOCKED FORMULA:
        battery_stress_score = (
            0.30 * temperature_score +
            0.20 * soc_score +
            0.20 * power_score +
            0.15 * driving_score +
            0.15 * charging_score
        )

    All component scores are normalized to 0-100.
    Final score is clamped to 0-100.

    C-rate proxy:
        c_rate = abs(battery_power_kw) / usable_battery_capacity_kwh
        Using 57 kWh usable capacity.
    """

    def __init__(self, config: IntelligenceConfig = DEFAULT_CONFIG):
        """Initialize battery stress analyzer.

        Args:
            config: Intelligence configuration
        """
        self.config = config

    def analyze(self, features: TelemetryFeatures) -> BatteryStressResult:
        """Analyze battery stress from telemetry features.

        Args:
            features: Extracted telemetry features

        Returns:
            BatteryStressResult with stress score and components
        """
        components = []

        # Temperature stress (weight: 0.30)
        temp_score = self._calculate_temperature_stress(features)
        temp_component = StressComponent(
            name="Temperature",
            raw_score=temp_score,
            weight=self.config.stress_weight_temperature,
            weighted_score=temp_score * self.config.stress_weight_temperature,
            description=self._describe_temp_stress(temp_score, features),
        )
        components.append(temp_component)

        # SOC stress (weight: 0.20)
        soc_score = self._calculate_soc_stress(features)
        soc_component = StressComponent(
            name="SOC Range",
            raw_score=soc_score,
            weight=self.config.stress_weight_soc,
            weighted_score=soc_score * self.config.stress_weight_soc,
            description=self._describe_soc_stress(soc_score, features),
        )
        components.append(soc_component)

        # Power stress (weight: 0.20)
        power_score = self._calculate_power_stress(features)
        power_component = StressComponent(
            name="Power Load",
            raw_score=power_score,
            weight=self.config.stress_weight_power,
            weighted_score=power_score * self.config.stress_weight_power,
            description=self._describe_power_stress(power_score, features),
        )
        components.append(power_component)

        # Driving stress (weight: 0.15)
        driving_score = self._calculate_driving_stress(features)
        driving_component = StressComponent(
            name="Driving Style",
            raw_score=driving_score,
            weight=self.config.stress_weight_driving,
            weighted_score=driving_score * self.config.stress_weight_driving,
            description=self._describe_driving_stress(driving_score, features),
        )
        components.append(driving_component)

        # Charging stress (weight: 0.15)
        charging_score = self._calculate_charging_stress(features)
        charging_component = StressComponent(
            name="Charging",
            raw_score=charging_score,
            weight=self.config.stress_weight_charging,
            weighted_score=charging_score * self.config.stress_weight_charging,
            description=self._describe_charging_stress(charging_score, features),
        )
        components.append(charging_component)

        # Calculate total stress score
        total_stress = sum(c.weighted_score for c in components)
        total_stress = max(0.0, min(100.0, total_stress))

        # Determine stress level
        stress_level = self._determine_stress_level(total_stress)

        # Generate explanation
        explanation = self._generate_explanation(components, total_stress, stress_level)

        return BatteryStressResult(
            battery_stress_score=round(total_stress, self.config.score_precision),
            stress_level=stress_level,
            components=components,
            explanation=explanation,
            c_rate_average=round(features.estimated_c_rate_average, 3),
            c_rate_max=round(features.estimated_c_rate_max, 3),
            high_temperature_exposure_percent=round(
                features.high_temperature_exposure_ratio * 100, self.config.percentage_precision
            ),
        )

    def _calculate_temperature_stress(self, features: TelemetryFeatures) -> float:
        """Calculate temperature stress score (0-100).

        Higher stress for temperatures outside optimal range.
        """
        avg_temp = features.battery_temperature_average_c
        max_temp = features.battery_temperature_max_c

        # Base score from average temperature
        if avg_temp < self.config.optimal_temperature_min_c:
            # Too cold
            cold_deviation = self.config.optimal_temperature_min_c - avg_temp
            base_score = min(cold_deviation * 5, 50)  # Max 50 from cold
        elif avg_temp > self.config.optimal_temperature_max_c:
            # Too hot
            hot_deviation = avg_temp - self.config.optimal_temperature_max_c
            base_score = min(hot_deviation * 10, 80)  # Max 80 from hot
        else:
            base_score = 0

        # Add penalty for max temperature peaks
        if max_temp > self.config.high_temperature_threshold_c:
            peak_deviation = max_temp - self.config.high_temperature_threshold_c
            base_score += min(peak_deviation * 5, 20)

        # Add penalty for high temperature exposure time
        exposure_penalty = features.high_temperature_exposure_ratio * 30

        total = base_score + exposure_penalty
        return max(0.0, min(100.0, total))

    def _calculate_soc_stress(self, features: TelemetryFeatures) -> float:
        """Calculate SOC stress score (0-100).

        Higher stress for deep discharges and wide SOC swings.
        """
        score = 0.0

        # Penalty for low SOC
        if features.min_soc_percent < self.config.low_soc_threshold_percent:
            depth = self.config.low_soc_threshold_percent - features.min_soc_percent
            score += min(depth * 3, 40)  # Max 40 from deep discharge

        # Penalty for deep discharge (below 10%)
        if features.min_soc_percent < self.config.deep_discharge_threshold_percent:
            score += 20

        # Penalty for time at low SOC
        if features.duration_seconds > 0:
            low_soc_ratio = features.time_below_low_soc_seconds / features.duration_seconds
            score += low_soc_ratio * 20

        # Penalty for wide SOC swing
        if features.soc_swing_percent > 60:
            swing_penalty = (features.soc_swing_percent - 60) * 0.5
            score += min(swing_penalty, 20)

        return max(0.0, min(100.0, score))

    def _calculate_power_stress(self, features: TelemetryFeatures) -> float:
        """Calculate power stress score (0-100).

        Higher stress for high power draw and high C-rates.
        """
        score = 0.0

        # C-rate based stress
        if features.estimated_c_rate_average > self.config.high_c_rate_threshold:
            c_rate_penalty = (
                features.estimated_c_rate_average - self.config.high_c_rate_threshold
            ) * 40
            score += min(c_rate_penalty, 50)

        # Peak C-rate penalty
        if features.estimated_c_rate_max > self.config.critical_c_rate_threshold:
            peak_penalty = (
                features.estimated_c_rate_max - self.config.critical_c_rate_threshold
            ) * 20
            score += min(peak_penalty, 30)

        # High power exposure
        score += features.high_power_exposure_ratio * 30

        return max(0.0, min(100.0, score))

    def _calculate_driving_stress(self, features: TelemetryFeatures) -> float:
        """Calculate driving style stress score (0-100).

        Higher stress for aggressive driving patterns.
        """
        score = 0.0

        # Aggressive driving score contribution
        score += min(features.aggressive_driving_score_average, 50)

        # Harsh events contribution
        if features.sample_count > 0:
            harsh_ratio = (
                features.harsh_acceleration_count + features.harsh_braking_count
            ) / features.sample_count
            score += min(harsh_ratio * 200, 30)

        # High acceleration contribution
        if features.max_acceleration_mps2 > self.config.high_acceleration_threshold_mps2:
            accel_penalty = (
                features.max_acceleration_mps2 - self.config.high_acceleration_threshold_mps2
            ) * 10
            score += min(accel_penalty, 20)

        return max(0.0, min(100.0, score))

    def _calculate_charging_stress(self, features: TelemetryFeatures) -> float:
        """Calculate charging stress score (0-100).

        Higher stress for high-power charging, especially at high temperatures.
        """
        if not features.is_charging_session:
            return 0.0

        score = 0.0

        # Fast charging C-rate
        if features.estimated_c_rate_average > 1.0:  # Above 1C charging
            c_rate_penalty = (features.estimated_c_rate_average - 1.0) * 30
            score += min(c_rate_penalty, 50)

        # High temperature during charging
        if features.battery_temperature_average_c > self.config.high_temperature_threshold_c:
            temp_penalty = (
                features.battery_temperature_average_c - self.config.high_temperature_threshold_c
            ) * 5
            score += min(temp_penalty, 30)

        # Charging at high SOC
        if features.max_soc_percent > self.config.high_soc_threshold_percent:
            high_soc_ratio = features.time_above_high_soc_seconds / max(
                features.duration_seconds, self.config.epsilon
            )
            score += high_soc_ratio * 20

        return max(0.0, min(100.0, score))

    def _determine_stress_level(self, score: float) -> StressLevel:
        """Determine stress level from score.

        Args:
            score: Stress score (0-100)

        Returns:
            StressLevel enum
        """
        if score < 25:
            return StressLevel.LOW
        elif score < 50:
            return StressLevel.MODERATE
        elif score < 75:
            return StressLevel.ELEVATED
        elif score < 90:
            return StressLevel.HIGH
        else:
            return StressLevel.CRITICAL

    def _generate_explanation(
        self, components: List[StressComponent], total_score: float, level: StressLevel
    ) -> str:
        """Generate explanation of stress analysis.

        Args:
            components: Stress components
            total_score: Total stress score
            level: Stress level

        Returns:
            Explanation string
        """
        # Sort by weighted score descending
        sorted_components = sorted(
            components, key=lambda c: c.weighted_score, reverse=True
        )

        # Find top contributors
        top_contributors = [c for c in sorted_components if c.raw_score > 30][:2]

        if level == StressLevel.LOW:
            return "Operational stress levels are low. Driving conditions are favorable for battery longevity."
        elif level == StressLevel.MODERATE:
            if top_contributors:
                names = " and ".join(c.name for c in top_contributors)
                return f"Moderate operational stress detected. Primary factors: {names}."
            return "Moderate operational stress detected during this driving session."
        else:
            if top_contributors:
                names = " and ".join(c.name for c in top_contributors)
                return f"Elevated operational stress detected. Key contributors: {names}. Consider adjustments to reduce stress."
            return f"Elevated operational stress detected (score: {total_score:.0f}/100). Review driving conditions."

    def _describe_temp_stress(self, score: float, features: TelemetryFeatures) -> str:
        """Describe temperature stress."""
        if score < 20:
            return f"Battery temperature normal (avg: {features.battery_temperature_average_c:.1f}\u00b0C)"
        elif score < 50:
            return f"Slightly elevated temperature stress (max: {features.battery_temperature_max_c:.1f}\u00b0C)"
        else:
            return f"High temperature stress (max: {features.battery_temperature_max_c:.1f}\u00b0C, {features.high_temperature_exposure_ratio*100:.0f}% exposure)"

    def _describe_soc_stress(self, score: float, features: TelemetryFeatures) -> str:
        """Describe SOC stress."""
        if score < 20:
            return f"SOC range normal ({features.min_soc_percent:.0f}%-{features.max_soc_percent:.0f}%)"
        elif score < 50:
            return f"Moderate SOC swing ({features.soc_swing_percent:.0f}% range)"
        else:
            return f"Wide SOC swing or deep discharge (min: {features.min_soc_percent:.0f}%)"

    def _describe_power_stress(self, score: float, features: TelemetryFeatures) -> str:
        """Describe power stress."""
        if score < 20:
            return f"Power demand normal (avg C-rate: {features.estimated_c_rate_average:.2f})"
        elif score < 50:
            return f"Moderate power demand (peak C-rate: {features.estimated_c_rate_max:.2f})"
        else:
            return f"High power stress (peak C-rate: {features.estimated_c_rate_max:.2f}, {features.high_power_exposure_ratio*100:.0f}% high-power time)"

    def _describe_driving_stress(self, score: float, features: TelemetryFeatures) -> str:
        """Describe driving style stress."""
        if score < 20:
            return "Smooth driving pattern"
        elif score < 50:
            return f"Moderate driving intensity (aggressive score: {features.aggressive_driving_score_average:.0f})"
        else:
            return f"Aggressive driving pattern ({features.harsh_acceleration_count} harsh accel, {features.harsh_braking_count} harsh brake events)"

    def _describe_charging_stress(self, score: float, features: TelemetryFeatures) -> str:
        """Describe charging stress."""
        if not features.is_charging_session:
            return "No charging stress (driving session)"
        if score < 20:
            return "Normal charging conditions"
        elif score < 50:
            return "Moderate charging stress"
        else:
            return f"High charging stress (C-rate: {features.estimated_c_rate_average:.2f})"
