"""Shared feature extraction for intelligence analysis.

This module provides a centralized feature extraction layer that all
intelligence modules consume. Features are extracted once and shared,
avoiding redundant calculations and ensuring consistency.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List, Optional
from app.db.models import Telemetry
from app.intelligence.config import IntelligenceConfig, DEFAULT_CONFIG


@dataclass
class TelemetryFeatures:
    """Extracted features from telemetry data.

    All intelligence modules should consume this structure rather than
    independently reimplementing telemetry calculations.
    """

    # === Time & Distance ===
    duration_seconds: float
    distance_km: float
    sample_count: int

    # === Speed Statistics ===
    average_speed_kmh: float
    max_speed_kmh: float
    min_speed_kmh: float

    # === Acceleration Statistics ===
    average_acceleration_mps2: float
    max_acceleration_mps2: float
    min_acceleration_mps2: float  # Includes braking (negative)

    # === Energy Metrics ===
    energy_consumed_kwh: float
    energy_regenerated_kwh: float
    net_energy_kwh: float
    energy_per_km: Optional[float]  # None if distance is zero
    efficiency_kwh_per_100km: Optional[float]  # None if distance is zero

    # === Battery Power Statistics ===
    battery_power_average_kw: float
    battery_power_peak_kw: float  # Max discharge
    battery_power_min_kw: float  # Min (most negative = charging)

    # === Battery Temperature Statistics ===
    battery_temperature_average_c: float
    battery_temperature_max_c: float
    battery_temperature_min_c: float

    # === Ambient Temperature Statistics ===
    ambient_temperature_average_c: float
    ambient_temperature_max_c: float
    ambient_temperature_min_c: float

    # === SOC Statistics ===
    starting_soc_percent: float
    ending_soc_percent: float
    soc_delta_percent: float
    min_soc_percent: float
    max_soc_percent: float

    # === Charging Metrics ===
    charging_energy_kwh: float
    charging_duration_seconds: float
    is_charging_session: bool

    # === Regen Metrics ===
    regen_ratio: Optional[float]  # regen / consumed, None if consumed is zero

    # === Exposure Metrics ===
    high_temperature_exposure_seconds: float
    high_temperature_exposure_ratio: float  # Fraction of time at high temp
    high_power_exposure_seconds: float
    high_power_exposure_ratio: float  # Fraction of time at high power

    # === Stress Indicators ===
    estimated_c_rate_average: float
    estimated_c_rate_max: float
    harsh_acceleration_count: int
    harsh_braking_count: int
    aggressive_driving_score_average: float

    # === Deep SOC Metrics ===
    time_below_low_soc_seconds: float
    time_above_high_soc_seconds: float
    soc_swing_percent: float  # Max - Min SOC during session

    # === Timestamps ===
    start_time: Optional[datetime]
    end_time: Optional[datetime]

    # === Validity ===
    is_valid: bool
    validation_message: str


class FeatureExtractor:
    """Extracts normalized features from telemetry data.

    This class provides the single source of truth for feature extraction.
    All intelligence modules must use this rather than implementing their
    own telemetry calculations.
    """

    def __init__(self, config: IntelligenceConfig = DEFAULT_CONFIG):
        """Initialize feature extractor.

        Args:
            config: Intelligence configuration with thresholds
        """
        self.config = config

    def extract(self, telemetry: List[Telemetry]) -> TelemetryFeatures:
        """Extract features from a list of telemetry records.

        Args:
            telemetry: List of Telemetry records, should be ordered by timestamp

        Returns:
            TelemetryFeatures with all extracted metrics
        """
        if not telemetry:
            return self._empty_features("No telemetry data provided")

        if len(telemetry) == 1:
            return self._single_point_features(telemetry[0])

        # Sort by timestamp to ensure correct ordering
        sorted_telemetry = sorted(telemetry, key=lambda t: t.timestamp)

        return self._extract_from_sorted(sorted_telemetry)

    def _empty_features(self, message: str) -> TelemetryFeatures:
        """Return empty features with validation message."""
        return TelemetryFeatures(
            duration_seconds=0.0,
            distance_km=0.0,
            sample_count=0,
            average_speed_kmh=0.0,
            max_speed_kmh=0.0,
            min_speed_kmh=0.0,
            average_acceleration_mps2=0.0,
            max_acceleration_mps2=0.0,
            min_acceleration_mps2=0.0,
            energy_consumed_kwh=0.0,
            energy_regenerated_kwh=0.0,
            net_energy_kwh=0.0,
            energy_per_km=None,
            efficiency_kwh_per_100km=None,
            battery_power_average_kw=0.0,
            battery_power_peak_kw=0.0,
            battery_power_min_kw=0.0,
            battery_temperature_average_c=0.0,
            battery_temperature_max_c=0.0,
            battery_temperature_min_c=0.0,
            ambient_temperature_average_c=0.0,
            ambient_temperature_max_c=0.0,
            ambient_temperature_min_c=0.0,
            starting_soc_percent=0.0,
            ending_soc_percent=0.0,
            soc_delta_percent=0.0,
            min_soc_percent=0.0,
            max_soc_percent=0.0,
            charging_energy_kwh=0.0,
            charging_duration_seconds=0.0,
            is_charging_session=False,
            regen_ratio=None,
            high_temperature_exposure_seconds=0.0,
            high_temperature_exposure_ratio=0.0,
            high_power_exposure_seconds=0.0,
            high_power_exposure_ratio=0.0,
            estimated_c_rate_average=0.0,
            estimated_c_rate_max=0.0,
            harsh_acceleration_count=0,
            harsh_braking_count=0,
            aggressive_driving_score_average=0.0,
            time_below_low_soc_seconds=0.0,
            time_above_high_soc_seconds=0.0,
            soc_swing_percent=0.0,
            start_time=None,
            end_time=None,
            is_valid=False,
            validation_message=message,
        )

    def _single_point_features(self, point: Telemetry) -> TelemetryFeatures:
        """Extract features from a single telemetry point."""
        c_rate = abs(point.battery_power_kw) / max(
            self.config.usable_battery_capacity_kwh, self.config.epsilon
        )

        return TelemetryFeatures(
            duration_seconds=0.0,
            distance_km=0.0,
            sample_count=1,
            average_speed_kmh=point.speed_kmh,
            max_speed_kmh=point.speed_kmh,
            min_speed_kmh=point.speed_kmh,
            average_acceleration_mps2=point.acceleration_mps2,
            max_acceleration_mps2=point.acceleration_mps2,
            min_acceleration_mps2=point.acceleration_mps2,
            energy_consumed_kwh=point.energy_consumed_kwh,
            energy_regenerated_kwh=point.regenerative_energy_kwh,
            net_energy_kwh=point.energy_consumed_kwh - point.regenerative_energy_kwh,
            energy_per_km=None,
            efficiency_kwh_per_100km=None,
            battery_power_average_kw=point.battery_power_kw,
            battery_power_peak_kw=point.battery_power_kw,
            battery_power_min_kw=point.battery_power_kw,
            battery_temperature_average_c=point.battery_temperature_c,
            battery_temperature_max_c=point.battery_temperature_c,
            battery_temperature_min_c=point.battery_temperature_c,
            ambient_temperature_average_c=point.ambient_temperature_c,
            ambient_temperature_max_c=point.ambient_temperature_c,
            ambient_temperature_min_c=point.ambient_temperature_c,
            starting_soc_percent=point.soc_percent,
            ending_soc_percent=point.soc_percent,
            soc_delta_percent=0.0,
            min_soc_percent=point.soc_percent,
            max_soc_percent=point.soc_percent,
            charging_energy_kwh=0.0,
            charging_duration_seconds=0.0,
            is_charging_session=point.charging,
            regen_ratio=None,
            high_temperature_exposure_seconds=0.0,
            high_temperature_exposure_ratio=0.0,
            high_power_exposure_seconds=0.0,
            high_power_exposure_ratio=0.0,
            estimated_c_rate_average=c_rate,
            estimated_c_rate_max=c_rate,
            harsh_acceleration_count=1 if point.harsh_acceleration else 0,
            harsh_braking_count=1 if point.harsh_braking else 0,
            aggressive_driving_score_average=point.aggressive_driving_score,
            time_below_low_soc_seconds=0.0,
            time_above_high_soc_seconds=0.0,
            soc_swing_percent=0.0,
            start_time=point.timestamp,
            end_time=point.timestamp,
            is_valid=True,
            validation_message="Single telemetry point - limited analysis possible",
        )

    def _extract_from_sorted(self, telemetry: List[Telemetry]) -> TelemetryFeatures:
        """Extract features from sorted telemetry list."""
        n = len(telemetry)
        first = telemetry[0]
        last = telemetry[-1]

        # Duration
        duration = (last.timestamp - first.timestamp).total_seconds()

        # Distance
        distance = last.trip_distance_km - first.trip_distance_km
        if distance < 0:
            # Handle case where trip was reset (fresh simulation)
            distance = last.trip_distance_km

        # Accumulate statistics
        speed_sum = 0.0
        speed_max = float("-inf")
        speed_min = float("inf")

        accel_sum = 0.0
        accel_max = float("-inf")
        accel_min = float("inf")

        power_sum = 0.0
        power_max = float("-inf")
        power_min = float("inf")

        bat_temp_sum = 0.0
        bat_temp_max = float("-inf")
        bat_temp_min = float("inf")

        amb_temp_sum = 0.0
        amb_temp_max = float("-inf")
        amb_temp_min = float("inf")

        soc_min = float("inf")
        soc_max = float("-inf")

        energy_consumed_total = 0.0
        energy_regen_total = 0.0
        charging_energy = 0.0

        c_rate_sum = 0.0
        c_rate_max = 0.0

        aggressive_sum = 0.0
        harsh_accel_count = 0
        harsh_brake_count = 0

        high_temp_samples = 0
        high_power_samples = 0
        low_soc_samples = 0
        high_soc_samples = 0
        charging_samples = 0

        for t in telemetry:
            # Speed
            speed_sum += t.speed_kmh
            speed_max = max(speed_max, t.speed_kmh)
            speed_min = min(speed_min, t.speed_kmh)

            # Acceleration
            accel_sum += t.acceleration_mps2
            accel_max = max(accel_max, t.acceleration_mps2)
            accel_min = min(accel_min, t.acceleration_mps2)

            # Power
            power_sum += t.battery_power_kw
            power_max = max(power_max, t.battery_power_kw)
            power_min = min(power_min, t.battery_power_kw)

            # Battery temperature
            bat_temp_sum += t.battery_temperature_c
            bat_temp_max = max(bat_temp_max, t.battery_temperature_c)
            bat_temp_min = min(bat_temp_min, t.battery_temperature_c)

            # Ambient temperature
            amb_temp_sum += t.ambient_temperature_c
            amb_temp_max = max(amb_temp_max, t.ambient_temperature_c)
            amb_temp_min = min(amb_temp_min, t.ambient_temperature_c)

            # SOC
            soc_min = min(soc_min, t.soc_percent)
            soc_max = max(soc_max, t.soc_percent)

            # Energy - accumulated values
            energy_consumed_total = max(energy_consumed_total, t.energy_consumed_kwh)
            energy_regen_total = max(energy_regen_total, t.regenerative_energy_kwh)

            # Charging energy
            if t.charging:
                charging_samples += 1
                # Charging power is positive, but we need to estimate energy
                # from power over interval. Since telemetry energy_consumed is
                # accumulated from start, we track charging state separately

            # C-rate
            c_rate = abs(t.battery_power_kw) / max(
                self.config.usable_battery_capacity_kwh, self.config.epsilon
            )
            c_rate_sum += c_rate
            c_rate_max = max(c_rate_max, c_rate)

            # Driving behavior
            aggressive_sum += t.aggressive_driving_score
            if t.harsh_acceleration:
                harsh_accel_count += 1
            if t.harsh_braking:
                harsh_brake_count += 1

            # Exposure tracking
            if t.battery_temperature_c >= self.config.high_temperature_threshold_c:
                high_temp_samples += 1
            if t.battery_power_kw >= self.config.high_power_threshold_kw:
                high_power_samples += 1
            if t.soc_percent < self.config.low_soc_threshold_percent:
                low_soc_samples += 1
            if t.soc_percent > self.config.high_soc_threshold_percent:
                high_soc_samples += 1

        # For charging energy, estimate from SOC change if charging session
        # SOC increase * capacity gives approximate charging energy
        starting_soc = first.soc_percent
        ending_soc = last.soc_percent
        soc_delta = ending_soc - starting_soc

        # If SOC increased, we had charging
        if soc_delta > 0:
            # Estimate charging energy from SOC increase
            charging_energy = (soc_delta / 100.0) * self.config.usable_battery_capacity_kwh

        # Calculate interval for exposure time
        interval_seconds = duration / max(n - 1, 1) if n > 1 else 0

        # Calculate averages
        avg_speed = speed_sum / n
        avg_accel = accel_sum / n
        avg_power = power_sum / n
        avg_bat_temp = bat_temp_sum / n
        avg_amb_temp = amb_temp_sum / n
        avg_c_rate = c_rate_sum / n
        avg_aggressive = aggressive_sum / n

        # Net energy
        net_energy = energy_consumed_total - energy_regen_total

        # Efficiency metrics - only if distance > 0
        if distance > self.config.epsilon:
            energy_per_km = net_energy / distance
            efficiency_kwh_per_100km = energy_per_km * 100
        else:
            energy_per_km = None
            efficiency_kwh_per_100km = None

        # Regen ratio
        if energy_consumed_total > self.config.epsilon:
            regen_ratio = energy_regen_total / energy_consumed_total
        else:
            regen_ratio = None

        # Is this a charging session?
        is_charging_session = charging_samples > (n / 2)  # More than half of samples charging

        # Exposure times
        high_temp_time = high_temp_samples * interval_seconds
        high_power_time = high_power_samples * interval_seconds
        low_soc_time = low_soc_samples * interval_seconds
        high_soc_time = high_soc_samples * interval_seconds
        charging_duration = charging_samples * interval_seconds

        # Exposure ratios
        high_temp_ratio = high_temp_samples / n if n > 0 else 0
        high_power_ratio = high_power_samples / n if n > 0 else 0

        # SOC swing
        soc_swing = soc_max - soc_min

        return TelemetryFeatures(
            duration_seconds=duration,
            distance_km=distance,
            sample_count=n,
            average_speed_kmh=avg_speed,
            max_speed_kmh=speed_max,
            min_speed_kmh=speed_min,
            average_acceleration_mps2=avg_accel,
            max_acceleration_mps2=accel_max,
            min_acceleration_mps2=accel_min,
            energy_consumed_kwh=energy_consumed_total,
            energy_regenerated_kwh=energy_regen_total,
            net_energy_kwh=net_energy,
            energy_per_km=energy_per_km,
            efficiency_kwh_per_100km=efficiency_kwh_per_100km,
            battery_power_average_kw=avg_power,
            battery_power_peak_kw=power_max,
            battery_power_min_kw=power_min,
            battery_temperature_average_c=avg_bat_temp,
            battery_temperature_max_c=bat_temp_max,
            battery_temperature_min_c=bat_temp_min,
            ambient_temperature_average_c=avg_amb_temp,
            ambient_temperature_max_c=amb_temp_max,
            ambient_temperature_min_c=amb_temp_min,
            starting_soc_percent=starting_soc,
            ending_soc_percent=ending_soc,
            soc_delta_percent=soc_delta,
            min_soc_percent=soc_min,
            max_soc_percent=soc_max,
            charging_energy_kwh=charging_energy,
            charging_duration_seconds=charging_duration,
            is_charging_session=is_charging_session,
            regen_ratio=regen_ratio,
            high_temperature_exposure_seconds=high_temp_time,
            high_temperature_exposure_ratio=high_temp_ratio,
            high_power_exposure_seconds=high_power_time,
            high_power_exposure_ratio=high_power_ratio,
            estimated_c_rate_average=avg_c_rate,
            estimated_c_rate_max=c_rate_max,
            harsh_acceleration_count=harsh_accel_count,
            harsh_braking_count=harsh_brake_count,
            aggressive_driving_score_average=avg_aggressive,
            time_below_low_soc_seconds=low_soc_time,
            time_above_high_soc_seconds=high_soc_time,
            soc_swing_percent=soc_swing,
            start_time=first.timestamp,
            end_time=last.timestamp,
            is_valid=True,
            validation_message="Features extracted successfully",
        )
