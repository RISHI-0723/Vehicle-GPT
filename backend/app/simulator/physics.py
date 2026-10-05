"""EV physics simulation utilities.

This module provides simplified physics calculations for EV telemetry simulation.
This is a prototype simulator, not a scientific battery model.

Sign conventions:
- battery_power_kw: positive = discharging, negative = charging
- pack_current_a: positive = discharging, negative = charging
- regenerative_energy_kwh: always non-negative
- charging_power_kw: 0 when not charging, positive when charging
"""
import random
from dataclasses import dataclass
from typing import Optional


@dataclass
class EVPhysics:
    """EV physics calculations for telemetry correlation.

    All calculations use simplified models appropriate for a prototype simulator.
    Values are correlated to maintain physical plausibility.
    """

    # Vehicle parameters
    battery_capacity_kwh: float = 60.0
    usable_capacity_kwh: float = 57.0
    nominal_voltage: float = 400.0  # Nominal pack voltage
    vehicle_mass_kg: float = 1800.0  # Approximate EV mass

    # Efficiency parameters
    base_consumption_kwh_per_km: float = 0.15  # ~15 kWh/100km base
    hvac_load_kw: float = 2.0  # Base HVAC load
    auxiliary_load_kw: float = 0.5  # Base auxiliary load

    # Regeneration parameters
    regen_efficiency: float = 0.7  # 70% of braking energy recovered
    max_regen_power_kw: float = 50.0  # Maximum regen power

    # Charging parameters
    max_charging_power_kw: float = 150.0  # DC fast charging
    charging_efficiency: float = 0.92  # 92% charging efficiency

    def calculate_power_demand(
        self,
        speed_kmh: float,
        acceleration_mps2: float,
        gradient_percent: float,
        ambient_temp_c: float,
        rng: random.Random,
    ) -> tuple[float, float, float]:
        """Calculate power demand based on driving conditions.

        Returns:
            tuple: (battery_power_kw, consumption_kwh_per_100km, hvac_load_kw)
                   battery_power_kw is positive for discharge.
        """
        if speed_kmh <= 0:
            # Stationary - only auxiliary loads
            aux_load = self.auxiliary_load_kw * (0.9 + 0.2 * rng.random())
            hvac = self._calculate_hvac_load(ambient_temp_c, rng)
            return aux_load + hvac, 0.0, hvac

        # Base rolling resistance and aerodynamic drag
        # Power = rolling_resistance + aero_drag + gradient + acceleration

        # Simplified model: power scales roughly with speed^2 for aero
        speed_ms = speed_kmh / 3.6
        aero_power = 0.0003 * speed_kmh ** 2  # kW, simplified

        # Rolling resistance (relatively constant with speed)
        rolling_power = 0.01 * self.vehicle_mass_kg * 9.81 * speed_ms / 1000  # kW

        # Gradient contribution
        gradient_power = self.vehicle_mass_kg * 9.81 * (gradient_percent / 100) * speed_ms / 1000

        # Acceleration contribution
        accel_power = self.vehicle_mass_kg * acceleration_mps2 * speed_ms / 1000

        # Total mechanical power
        mech_power = aero_power + rolling_power + gradient_power + accel_power

        # HVAC and auxiliary loads
        hvac_load = self._calculate_hvac_load(ambient_temp_c, rng)
        aux_load = self.auxiliary_load_kw * (0.9 + 0.2 * rng.random())

        # Total battery power (positive = discharge)
        # Include drivetrain efficiency (~90%)
        drivetrain_efficiency = 0.9
        battery_power = (mech_power / drivetrain_efficiency if mech_power > 0 else mech_power * drivetrain_efficiency)
        battery_power += hvac_load + aux_load

        # Calculate consumption rate
        if speed_kmh > 0:
            consumption_per_100km = (battery_power / speed_kmh) * 100
        else:
            consumption_per_100km = 0.0

        # Ensure non-negative consumption display
        consumption_per_100km = max(0, consumption_per_100km)

        return battery_power, consumption_per_100km, hvac_load

    def _calculate_hvac_load(self, ambient_temp_c: float, rng: random.Random) -> float:
        """Calculate HVAC load based on ambient temperature."""
        # Comfortable cabin temp is ~22C
        comfort_temp = 22.0
        temp_diff = abs(ambient_temp_c - comfort_temp)

        if temp_diff < 5:
            # Minimal HVAC needed
            return 0.5 * (0.8 + 0.4 * rng.random())
        elif temp_diff < 15:
            # Moderate HVAC
            return self.hvac_load_kw * (0.8 + 0.4 * rng.random())
        else:
            # High HVAC load (very hot or cold)
            multiplier = 1.0 + (temp_diff - 15) / 20
            return self.hvac_load_kw * multiplier * (0.9 + 0.2 * rng.random())

    def calculate_regeneration(
        self,
        deceleration_mps2: float,
        speed_kmh: float,
        rng: random.Random,
    ) -> float:
        """Calculate regenerative braking energy recovery.

        Returns:
            Regenerated power in kW (always non-negative for regen energy tracking).
        """
        if deceleration_mps2 >= 0 or speed_kmh <= 5:
            return 0.0

        speed_ms = speed_kmh / 3.6
        # Kinetic energy rate being dissipated
        braking_power = abs(self.vehicle_mass_kg * deceleration_mps2 * speed_ms / 1000)

        # Apply regen efficiency and cap
        regen_power = min(braking_power * self.regen_efficiency, self.max_regen_power_kw)

        # Add small variation
        regen_power *= (0.9 + 0.2 * rng.random())

        return regen_power

    def calculate_pack_voltage(self, soc_percent: float, rng: random.Random) -> float:
        """Calculate pack voltage based on SOC.

        LFP batteries have relatively flat voltage curves.
        """
        # Simplified voltage model: 350V at 0% to 410V at 100%
        base_voltage = 350 + (soc_percent / 100) * 60
        # Small variation
        variation = rng.uniform(-2, 2)
        return base_voltage + variation

    def calculate_pack_current(
        self,
        battery_power_kw: float,
        pack_voltage_v: float,
    ) -> float:
        """Calculate pack current from power and voltage.

        Returns:
            Current in Amps. Positive = discharge, negative = charge.
        """
        if pack_voltage_v <= 0:
            return 0.0
        return (battery_power_kw * 1000) / pack_voltage_v

    def calculate_battery_temperature_change(
        self,
        current_temp_c: float,
        ambient_temp_c: float,
        power_kw: float,
        charging: bool,
        interval_seconds: float,
        rng: random.Random,
    ) -> float:
        """Calculate battery temperature change over time interval.

        Returns:
            New battery temperature in Celsius.
        """
        # Heat generation from power flow (simplified)
        heat_generation_rate = abs(power_kw) * 0.02  # C per kW per minute
        heat_per_interval = heat_generation_rate * (interval_seconds / 60)

        # Cooling towards ambient (simplified thermal model)
        temp_diff = current_temp_c - ambient_temp_c
        cooling_rate = 0.005  # C per degree diff per minute
        cooling_per_interval = temp_diff * cooling_rate * (interval_seconds / 60)

        # Charging tends to heat battery more
        if charging:
            heat_per_interval *= 1.3

        # New temperature
        new_temp = current_temp_c + heat_per_interval - cooling_per_interval

        # Small random variation
        new_temp += rng.uniform(-0.1, 0.1)

        # Physical bounds
        return max(-20, min(60, new_temp))

    def calculate_soc_change(
        self,
        current_soc: float,
        energy_delta_kwh: float,
    ) -> float:
        """Calculate new SOC after energy change.

        Args:
            current_soc: Current SOC percentage
            energy_delta_kwh: Energy change (negative = consumption, positive = charging)

        Returns:
            New SOC percentage, bounded 0-100.
        """
        soc_delta = (energy_delta_kwh / self.usable_capacity_kwh) * 100
        new_soc = current_soc + soc_delta
        return max(0.0, min(100.0, new_soc))

    def calculate_charging_power(
        self,
        soc_percent: float,
        max_power_kw: float,
        rng: random.Random,
    ) -> float:
        """Calculate charging power based on SOC (charging curve).

        DC fast charging typically tapers at high SOC.

        Returns:
            Charging power in kW (positive value).
        """
        if soc_percent >= 100:
            return 0.0

        # Charging curve: full power until ~80%, then taper
        if soc_percent < 80:
            power_factor = 1.0
        elif soc_percent < 90:
            power_factor = 1.0 - (soc_percent - 80) * 0.03  # Taper to 70%
        else:
            power_factor = 0.7 - (soc_percent - 90) * 0.05  # Taper more aggressively

        power_factor = max(0.1, power_factor)  # Minimum 10% power

        charging_power = max_power_kw * power_factor * (0.95 + 0.1 * rng.random())

        return max(0, charging_power)
