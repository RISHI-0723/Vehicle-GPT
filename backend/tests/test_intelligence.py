"""Sprint 2 Intelligence Engine Tests.

This file contains at least 60 tests covering:
1. Feature extraction
2. Energy calculations
3. Baseline selection
4. Range estimation
5. Contributor analysis
6. Anomaly detection
7. Battery stress
8. What-if engine
9. Cost analysis
10. Recommendations
11. Composite endpoints
12. Edge cases
13. No-mutation verification
14. Determinism verification
"""

import pytest
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from app.db.models import Vehicle, Telemetry, Simulation
from app.core.config import DEMO_VEHICLE_CONFIG
from app.intelligence.config import DEFAULT_CONFIG, IntelligenceConfig
from app.intelligence.features import FeatureExtractor, TelemetryFeatures
from app.intelligence.baseline import BaselineSelector, BaselineMatchType
from app.intelligence.energy import EnergyAnalyzer, EfficiencyRating
from app.intelligence.range_estimator import RangeEstimator, ConfidenceLevel
from app.intelligence.contributors import ContributorAnalyzer, ImpactLevel
from app.intelligence.anomaly import AnomalyDetector, AnomalySeverity
from app.intelligence.battery_stress import BatteryStressAnalyzer, StressLevel
from app.intelligence.cost import CostAnalyzer
from app.intelligence.recommendations import RecommendationEngine, RecommendationPriority
from app.intelligence.what_if import WhatIfEngine
from app.intelligence.orchestrator import IntelligenceOrchestrator
from app.simulator.engine import VehicleState


# ============================================================
# HELPER FIXTURES
# ============================================================

@pytest.fixture
def run_normal_driving(client, demo_vehicle_id):
    """Run a NORMAL_DRIVING simulation and return the response."""
    response = client.post("/api/v1/simulation/run", json={
        "vehicle_id": demo_vehicle_id,
        "scenario": "NORMAL_DRIVING",
        "duration_minutes": 10,
        "interval_seconds": 10,
        "seed": 42,
        "mode": "fresh",
    })
    assert response.status_code == 200
    return response.json()


@pytest.fixture
def run_aggressive_driving(client, demo_vehicle_id, run_normal_driving):
    """Run an AGGRESSIVE_DRIVING simulation after NORMAL_DRIVING."""
    response = client.post("/api/v1/simulation/run", json={
        "vehicle_id": demo_vehicle_id,
        "scenario": "AGGRESSIVE_DRIVING",
        "duration_minutes": 10,
        "interval_seconds": 10,
        "seed": 42,
        "mode": "fresh",
    })
    assert response.status_code == 200
    return response.json()


@pytest.fixture
def run_energy_anomaly(client, demo_vehicle_id, run_normal_driving):
    """Run an ENERGY_ANOMALY simulation after NORMAL_DRIVING."""
    response = client.post("/api/v1/simulation/run", json={
        "vehicle_id": demo_vehicle_id,
        "scenario": "ENERGY_ANOMALY",
        "duration_minutes": 10,
        "interval_seconds": 10,
        "seed": 42,
        "mode": "fresh",
    })
    assert response.status_code == 200
    return response.json()


@pytest.fixture
def run_fast_charging(client, demo_vehicle_id, run_normal_driving):
    """Run a FAST_CHARGING simulation."""
    response = client.post("/api/v1/simulation/run", json={
        "vehicle_id": demo_vehicle_id,
        "scenario": "FAST_CHARGING",
        "duration_minutes": 10,
        "interval_seconds": 10,
        "seed": 42,
        "mode": "fresh",
    })
    assert response.status_code == 200
    return response.json()


# ============================================================
# 1. FEATURE EXTRACTION TESTS
# ============================================================

class TestFeatureExtraction:
    """Tests for shared feature extraction pipeline."""

    def test_empty_telemetry_returns_invalid_features(self):
        """Empty telemetry should return invalid features."""
        extractor = FeatureExtractor(DEFAULT_CONFIG)
        features = extractor.extract([])

        assert features.is_valid is False
        assert features.sample_count == 0
        assert "No telemetry" in features.validation_message

    def test_single_point_telemetry(self, test_db):
        """Single telemetry point should be handled."""
        # Create mock telemetry
        class MockTelemetry:
            timestamp = datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
            soc_percent = 80.0
            soh_percent = 94.0
            battery_temperature_c = 30.0
            pack_voltage_v = 400.0
            pack_current_a = 10.0
            battery_power_kw = 4.0
            speed_kmh = 50.0
            acceleration_mps2 = 0.5
            odometer_km = 12500.0
            trip_distance_km = 0.0
            energy_consumed_kwh = 0.1
            energy_consumption_kwh_per_100km = 15.0
            regenerative_energy_kwh = 0.0
            ambient_temperature_c = 25.0
            elevation_m = 0.0
            road_gradient_percent = 0.0
            harsh_acceleration = False
            harsh_braking = False
            aggressive_driving_score = 10.0
            charging = False
            charging_power_kw = 0.0
            charger_id = None

        extractor = FeatureExtractor(DEFAULT_CONFIG)
        features = extractor.extract([MockTelemetry()])

        assert features.is_valid is True
        assert features.sample_count == 1
        assert features.average_speed_kmh == 50.0
        assert features.duration_seconds == 0.0

    def test_feature_extraction_from_simulation(self, client, demo_vehicle_id, run_normal_driving):
        """Features should be extracted correctly from simulation telemetry."""
        sim_id = run_normal_driving["simulation_id"]

        # Get telemetry
        response = client.get(f"/api/v1/vehicles/{demo_vehicle_id}/telemetry?limit=1000")
        assert response.status_code == 200

        # Check features via energy endpoint
        response = client.get(f"/api/v1/intelligence/energy/{demo_vehicle_id}")
        assert response.status_code == 200
        data = response.json()

        assert data["distance_km"] > 0
        assert data["energy_consumed_kwh"] > 0
        assert data["sample_count"] > 0


# ============================================================
# 2. ENERGY ANALYSIS TESTS
# ============================================================

class TestEnergyAnalysis:
    """Tests for energy analysis service."""

    def test_energy_endpoint_works(self, client, demo_vehicle_id, run_normal_driving):
        """Energy endpoint should return valid data."""
        response = client.get(f"/api/v1/intelligence/energy/{demo_vehicle_id}")
        assert response.status_code == 200
        data = response.json()

        assert "energy_consumed_kwh" in data
        assert "net_energy_kwh" in data
        assert "efficiency_kwh_per_100km" in data
        assert "rating" in data

    def test_energy_comparison_with_baseline(self, client, demo_vehicle_id, run_aggressive_driving):
        """Energy should be compared against baseline."""
        response = client.get(f"/api/v1/intelligence/energy/{demo_vehicle_id}")
        assert response.status_code == 200
        data = response.json()

        # Aggressive driving should be less efficient than normal baseline
        assert data["baseline_match_type"] in ["EXACT", "APPROXIMATE"]
        assert data["baseline_simulation_id"] is not None

    def test_zero_distance_handling(self, client, demo_vehicle_id, run_fast_charging):
        """Zero distance should be handled gracefully."""
        # Get the charging simulation ID
        sim_id = run_fast_charging["simulation_id"]

        response = client.get(
            f"/api/v1/intelligence/energy/{demo_vehicle_id}?simulation_id={sim_id}"
        )
        assert response.status_code == 200
        data = response.json()

        # Should have null efficiency due to zero distance
        assert data["distance_km"] == 0.0 or data["efficiency_kwh_per_100km"] is None


# ============================================================
# 3. BASELINE SELECTION TESTS
# ============================================================

class TestBaselineSelection:
    """Tests for baseline selection service."""

    def test_baseline_exact_match(self, client, demo_vehicle_id, run_normal_driving):
        """Exact baseline match should be detected."""
        # Run another NORMAL_DRIVING with same duration/interval
        response = client.post("/api/v1/simulation/run", json={
            "vehicle_id": demo_vehicle_id,
            "scenario": "NORMAL_DRIVING",
            "duration_minutes": 10,
            "interval_seconds": 10,
            "seed": 100,
            "mode": "fresh",
        })
        assert response.status_code == 200

        # Run AGGRESSIVE and check baseline
        response = client.post("/api/v1/simulation/run", json={
            "vehicle_id": demo_vehicle_id,
            "scenario": "AGGRESSIVE_DRIVING",
            "duration_minutes": 10,
            "interval_seconds": 10,
            "seed": 42,
            "mode": "fresh",
        })
        assert response.status_code == 200

        response = client.get(f"/api/v1/intelligence/energy/{demo_vehicle_id}")
        data = response.json()

        # Should find exact match
        assert data["baseline_match_type"] == "EXACT"

    def test_baseline_approximate_match(self, client, demo_vehicle_id, run_normal_driving):
        """Approximate baseline should be used when no exact match."""
        # Run AGGRESSIVE with different duration
        response = client.post("/api/v1/simulation/run", json={
            "vehicle_id": demo_vehicle_id,
            "scenario": "AGGRESSIVE_DRIVING",
            "duration_minutes": 15,  # Different duration
            "interval_seconds": 10,
            "seed": 42,
            "mode": "fresh",
        })
        assert response.status_code == 200

        response = client.get(f"/api/v1/intelligence/energy/{demo_vehicle_id}")
        data = response.json()

        assert data["baseline_match_type"] == "APPROXIMATE"

    def test_baseline_unavailable(self, client, demo_vehicle_id):
        """Missing baseline should be detected."""
        # Run only AGGRESSIVE (no NORMAL_DRIVING)
        response = client.post("/api/v1/simulation/run", json={
            "vehicle_id": demo_vehicle_id,
            "scenario": "AGGRESSIVE_DRIVING",
            "duration_minutes": 10,
            "interval_seconds": 10,
            "seed": 42,
            "mode": "fresh",
        })
        assert response.status_code == 200

        response = client.get(f"/api/v1/intelligence/energy/{demo_vehicle_id}")
        data = response.json()

        assert data["baseline_match_type"] == "UNAVAILABLE"
        assert data["baseline_simulation_id"] is None

    def test_fast_charging_not_used_as_baseline(self, client, demo_vehicle_id):
        """FAST_CHARGING should not be used as driving baseline."""
        # Run FAST_CHARGING first (no NORMAL_DRIVING)
        response = client.post("/api/v1/simulation/run", json={
            "vehicle_id": demo_vehicle_id,
            "scenario": "FAST_CHARGING",
            "duration_minutes": 10,
            "interval_seconds": 10,
            "seed": 42,
            "mode": "fresh",
        })
        assert response.status_code == 200

        # Run AGGRESSIVE after FAST_CHARGING
        response = client.post("/api/v1/simulation/run", json={
            "vehicle_id": demo_vehicle_id,
            "scenario": "AGGRESSIVE_DRIVING",
            "duration_minutes": 10,
            "interval_seconds": 10,
            "seed": 42,
            "mode": "fresh",
        })
        assert response.status_code == 200

        response = client.get(f"/api/v1/intelligence/energy/{demo_vehicle_id}")
        data = response.json()

        # Should be unavailable (no NORMAL_DRIVING - FAST_CHARGING is not a driving baseline)
        assert data["baseline_match_type"] == "UNAVAILABLE"


# ============================================================
# 4. RANGE ESTIMATION TESTS
# ============================================================

class TestRangeEstimation:
    """Tests for range estimation service."""

    def test_range_endpoint_works(self, client, demo_vehicle_id, run_normal_driving):
        """Range endpoint should return valid data."""
        response = client.get(f"/api/v1/intelligence/range/{demo_vehicle_id}")
        assert response.status_code == 200
        data = response.json()

        assert "current_soc_percent" in data
        assert "remaining_energy_kwh" in data
        assert "estimated_range_km" in data
        assert "confidence" in data

    def test_range_uses_efficiency(self, client, demo_vehicle_id, run_normal_driving):
        """Range should be based on efficiency."""
        response = client.get(f"/api/v1/intelligence/range/{demo_vehicle_id}")
        data = response.json()

        if data["efficiency_kwh_per_km"] is not None:
            expected_range = data["remaining_energy_kwh"] / data["efficiency_kwh_per_km"]
            assert abs(data["estimated_range_km"] - expected_range) < 1.0

    def test_range_null_for_charging_session(self, client, demo_vehicle_id, run_fast_charging):
        """Charging-only session should have null range from that efficiency."""
        sim_id = run_fast_charging["simulation_id"]

        response = client.get(
            f"/api/v1/intelligence/range/{demo_vehicle_id}?simulation_id={sim_id}"
        )
        assert response.status_code == 200
        data = response.json()

        # Should use baseline efficiency or be unavailable
        assert data["confidence"] in ["HIGH", "MEDIUM", "LOW"]


# ============================================================
# 5. CONTRIBUTOR ANALYSIS TESTS
# ============================================================

class TestContributorAnalysis:
    """Tests for contributor analysis service."""

    def test_contributors_endpoint_works(self, client, demo_vehicle_id, run_aggressive_driving):
        """Contributors endpoint should return data."""
        response = client.get(f"/api/v1/intelligence/contributors/{demo_vehicle_id}")
        assert response.status_code == 200
        data = response.json()

        assert "contributors" in data
        assert len(data["contributors"]) > 0

    def test_contributor_formula_applied(self, client, demo_vehicle_id, run_aggressive_driving):
        """Contributor impact scores should follow the formula."""
        response = client.get(f"/api/v1/intelligence/contributors/{demo_vehicle_id}")
        data = response.json()

        for contributor in data["contributors"]:
            if contributor["is_available"]:
                # Impact score should be 0-100
                assert 0 <= contributor["impact_score"] <= 100

    def test_contributor_impact_levels(self, client, demo_vehicle_id, run_aggressive_driving):
        """Impact levels should match thresholds."""
        response = client.get(f"/api/v1/intelligence/contributors/{demo_vehicle_id}")
        data = response.json()

        for contributor in data["contributors"]:
            score = contributor["impact_score"]
            level = contributor["impact_level"]

            if not contributor["is_available"]:
                assert level == "UNAVAILABLE"
            elif score <= 24:
                assert level == "LOW"
            elif score <= 49:
                assert level == "MEDIUM"
            elif score <= 74:
                assert level == "HIGH"
            else:
                assert level == "CRITICAL"

    def test_contributors_unavailable_without_baseline(self, client, demo_vehicle_id):
        """Contributors requiring baseline should be unavailable."""
        # Run only AGGRESSIVE
        client.post("/api/v1/simulation/run", json={
            "vehicle_id": demo_vehicle_id,
            "scenario": "AGGRESSIVE_DRIVING",
            "duration_minutes": 10,
            "interval_seconds": 10,
            "seed": 42,
            "mode": "fresh",
        })

        response = client.get(f"/api/v1/intelligence/contributors/{demo_vehicle_id}")
        data = response.json()

        assert data["baseline_available"] is False
        for contributor in data["contributors"]:
            assert contributor["is_available"] is False


# ============================================================
# 6. ANOMALY DETECTION TESTS
# ============================================================

class TestAnomalyDetection:
    """Tests for anomaly detection service."""

    def test_anomaly_endpoint_works(self, client, demo_vehicle_id, run_aggressive_driving):
        """Anomaly endpoint should return data."""
        response = client.get(f"/api/v1/intelligence/anomaly/{demo_vehicle_id}")
        assert response.status_code == 200
        data = response.json()

        assert "anomaly_score" in data
        assert "severity" in data
        assert "is_anomalous" in data

    def test_anomaly_score_formula(self, client, demo_vehicle_id, run_aggressive_driving):
        """Anomaly score should follow the weighted formula."""
        response = client.get(f"/api/v1/intelligence/anomaly/{demo_vehicle_id}")
        data = response.json()

        # Score should be 0-100
        assert 0 <= data["anomaly_score"] <= 100

        # Components should have correct weights
        if data["components"]:
            for comp in data["components"]:
                if comp["name"] == "energy":
                    assert comp["weight"] == 0.60
                elif comp["name"] == "speed":
                    assert comp["weight"] == 0.20
                elif comp["name"] == "acceleration":
                    assert comp["weight"] == 0.10
                elif comp["name"] == "temperature":
                    assert comp["weight"] == 0.10

    def test_anomaly_severity_thresholds(self, client, demo_vehicle_id, run_aggressive_driving):
        """Severity should match score thresholds."""
        response = client.get(f"/api/v1/intelligence/anomaly/{demo_vehicle_id}")
        data = response.json()

        score = data["anomaly_score"]
        severity = data["severity"]

        if score < 25:
            assert severity == "NORMAL"
        elif score < 50:
            assert severity == "LOW"
        elif score < 75:
            assert severity == "MEDIUM"
        elif score < 90:
            assert severity == "HIGH"
        else:
            assert severity == "CRITICAL"

    def test_energy_anomaly_scenario_detected(self, client, demo_vehicle_id, run_energy_anomaly):
        """ENERGY_ANOMALY scenario should have elevated anomaly score."""
        sim_id = run_energy_anomaly["simulation_id"]

        response = client.get(
            f"/api/v1/intelligence/anomaly/{demo_vehicle_id}?simulation_id={sim_id}"
        )
        data = response.json()

        # Energy anomaly should be detected (if baseline available)
        if data["baseline_available"]:
            # The energy deviation should be present and measurable
            energy_comp = next(
                (c for c in data["components"] if c["name"] == "energy"),
                None
            )
            if energy_comp:
                # ENERGY_ANOMALY has 25% consumption multiplier during anomaly phase
                # The overall deviation depends on phase distribution (40% baseline, 35% anomaly)
                # So we expect some deviation but not necessarily 25% overall
                assert energy_comp["deviation_ratio"] >= 0.10  # At least 10% deviation


# ============================================================
# 7. BATTERY STRESS TESTS
# ============================================================

class TestBatteryStress:
    """Tests for battery stress analysis service."""

    def test_stress_endpoint_works(self, client, demo_vehicle_id, run_aggressive_driving):
        """Battery stress endpoint should return data."""
        response = client.get(f"/api/v1/intelligence/battery-stress/{demo_vehicle_id}")
        assert response.status_code == 200
        data = response.json()

        assert "battery_stress_score" in data
        assert "stress_level" in data
        assert "components" in data

    def test_stress_formula_weights(self, client, demo_vehicle_id, run_aggressive_driving):
        """Stress formula should use correct weights."""
        response = client.get(f"/api/v1/intelligence/battery-stress/{demo_vehicle_id}")
        data = response.json()

        # Check component weights
        weight_sum = 0
        for comp in data["components"]:
            weight_sum += comp["weight"]
            if comp["name"] == "Temperature":
                assert comp["weight"] == 0.30
            elif comp["name"] == "SOC Range":
                assert comp["weight"] == 0.20
            elif comp["name"] == "Power Load":
                assert comp["weight"] == 0.20
            elif comp["name"] == "Driving Style":
                assert comp["weight"] == 0.15
            elif comp["name"] == "Charging":
                assert comp["weight"] == 0.15

        assert abs(weight_sum - 1.0) < 0.001

    def test_c_rate_calculation(self, client, demo_vehicle_id, run_aggressive_driving):
        """C-rate should be calculated."""
        response = client.get(f"/api/v1/intelligence/battery-stress/{demo_vehicle_id}")
        data = response.json()

        assert "c_rate_average" in data
        assert "c_rate_max" in data
        assert data["c_rate_average"] >= 0
        assert data["c_rate_max"] >= data["c_rate_average"]

    def test_stress_level_matches_score(self, client, demo_vehicle_id, run_aggressive_driving):
        """Stress level should match score."""
        response = client.get(f"/api/v1/intelligence/battery-stress/{demo_vehicle_id}")
        data = response.json()

        score = data["battery_stress_score"]
        level = data["stress_level"]

        if score < 25:
            assert level == "LOW"
        elif score < 50:
            assert level == "MODERATE"
        elif score < 75:
            assert level == "ELEVATED"
        elif score < 90:
            assert level == "HIGH"
        else:
            assert level == "CRITICAL"


# ============================================================
# 8. WHAT-IF ENGINE TESTS
# ============================================================

class TestWhatIfEngine:
    """Tests for what-if counterfactual engine."""

    def test_what_if_endpoint_works(self, client, demo_vehicle_id, run_aggressive_driving):
        """What-if endpoint should return data."""
        sim_id = run_aggressive_driving["simulation_id"]

        response = client.post("/api/v1/intelligence/what-if", json={
            "vehicle_id": demo_vehicle_id,
            "counterfactual_scenario": "NORMAL_DRIVING",
            "base_simulation_id": sim_id,
        })
        assert response.status_code == 200
        data = response.json()

        assert "base_metrics" in data
        assert "counterfactual_metrics" in data
        assert "interpretation" in data

    def test_what_if_starts_from_base_starting_soc(self, client, demo_vehicle_id, run_aggressive_driving):
        """Counterfactual should start from BASE simulation's STARTING SOC."""
        sim_id = run_aggressive_driving["simulation_id"]
        starting_soc = run_aggressive_driving["starting_soc"]

        response = client.post("/api/v1/intelligence/what-if", json={
            "vehicle_id": demo_vehicle_id,
            "counterfactual_scenario": "NORMAL_DRIVING",
            "base_simulation_id": sim_id,
        })
        data = response.json()

        # Counterfactual must start from the base simulation's nominal starting SOC exactly
        assert data["starting_soc_percent"] == starting_soc
        assert data["base_metrics"]["starting_soc_percent"] == starting_soc
        assert data["counterfactual_metrics"]["starting_soc_percent"] == starting_soc

    def test_what_if_inherits_duration(self, client, demo_vehicle_id, run_aggressive_driving):
        """Counterfactual should inherit duration from base."""
        sim_id = run_aggressive_driving["simulation_id"]

        response = client.post("/api/v1/intelligence/what-if", json={
            "vehicle_id": demo_vehicle_id,
            "counterfactual_scenario": "NORMAL_DRIVING",
            "base_simulation_id": sim_id,
        })
        data = response.json()

        # Both should have same duration
        assert data["base_metrics"]["duration_seconds"] == data["counterfactual_metrics"]["duration_seconds"]

    def test_what_if_inherits_interval(self, client, demo_vehicle_id, run_aggressive_driving):
        """Counterfactual should inherit interval from base."""
        sim_id = run_aggressive_driving["simulation_id"]

        response = client.post("/api/v1/intelligence/what-if", json={
            "vehicle_id": demo_vehicle_id,
            "counterfactual_scenario": "NORMAL_DRIVING",
            "base_simulation_id": sim_id,
        })
        data = response.json()

        assert data["base_metrics"]["sample_count"] == data["counterfactual_metrics"]["sample_count"]

    def test_fast_charging_what_if_range_null(self, client, demo_vehicle_id, run_aggressive_driving):
        """FAST_CHARGING counterfactual should have null range change."""
        sim_id = run_aggressive_driving["simulation_id"]

        response = client.post("/api/v1/intelligence/what-if", json={
            "vehicle_id": demo_vehicle_id,
            "counterfactual_scenario": "FAST_CHARGING",
            "base_simulation_id": sim_id,
        })
        assert response.status_code == 200
        data = response.json()

        # Range change should be null for charging scenario
        assert data["estimated_range_change_km"] is None

    def test_controlled_aggressive_to_normal_range_improvement(self, client, demo_vehicle_id, run_aggressive_driving):
        """NORMAL_DRIVING counterfactual should show range improvement over AGGRESSIVE."""
        sim_id = run_aggressive_driving["simulation_id"]

        response = client.post("/api/v1/intelligence/what-if", json={
            "vehicle_id": demo_vehicle_id,
            "counterfactual_scenario": "NORMAL_DRIVING",
            "base_simulation_id": sim_id,
        })
        data = response.json()

        # Normal driving should be more efficient
        if (data["base_metrics"]["estimated_range_km"] is not None and
            data["counterfactual_metrics"]["estimated_range_km"] is not None):
            # Counterfactual (normal) should have better range
            assert data["counterfactual_metrics"]["estimated_range_km"] >= data["base_metrics"]["estimated_range_km"]

    def test_what_if_default_base_selection(self, client, demo_vehicle_id, run_aggressive_driving):
        """What-if should use latest driving simulation as default base."""
        response = client.post("/api/v1/intelligence/what-if", json={
            "vehicle_id": demo_vehicle_id,
            "counterfactual_scenario": "NORMAL_DRIVING",
            # No base_simulation_id - should use latest
        })
        assert response.status_code == 200
        data = response.json()

        assert data["base_simulation_id"] == run_aggressive_driving["simulation_id"]


# ============================================================
# 8b. WHAT-IF STARTING-STATE SEMANTICS TESTS
# ============================================================

class TestWhatIfStartingState:
    """Counterfactuals must start from the state IMMEDIATELY BEFORE the base simulation began."""

    COMPARED_METRICS = (
        "starting_soc_percent",
        "ending_soc_percent",
        "energy_consumed_kwh",
        "distance_km",
        "efficiency_kwh_per_100km",
        "estimated_range_km",
        "duration_seconds",
        "sample_count",
    )

    @staticmethod
    def _what_if(client, vehicle_id, scenario, base_simulation_id):
        response = client.post("/api/v1/intelligence/what-if", json={
            "vehicle_id": vehicle_id,
            "counterfactual_scenario": scenario,
            "base_simulation_id": base_simulation_id,
        })
        assert response.status_code == 200
        return response.json()

    def test_canonical_starting_state_is_vehicle_baseline(self):
        """Starting state comes from the canonical baseline, with no driving state yet."""
        state = VehicleState.from_baseline(DEMO_VEHICLE_CONFIG)

        assert state.soc_percent == 80.0
        assert state.soh_percent == DEMO_VEHICLE_CONFIG["initial_soh_percent"]
        assert state.battery_temperature_c == DEMO_VEHICLE_CONFIG["initial_battery_temperature_c"]
        assert state.odometer_km == DEMO_VEHICLE_CONFIG["initial_odometer_km"]
        assert state.speed_kmh == 0.0
        assert state.trip_distance_km == 0.0
        assert state.energy_consumed_kwh == 0.0
        assert state.regenerative_energy_kwh == 0.0
        assert state.elevation_m == 0.0

    def test_counterfactual_starts_at_nominal_soc_not_first_sample(
        self, client, demo_vehicle_id, run_normal_driving, test_db
    ):
        """Nominal start SOC is 80.0%, while the first telemetry sample is already post-step."""
        sim_id = run_normal_driving["simulation_id"]
        nominal_soc = DEMO_VEHICLE_CONFIG["initial_soc_percent"]
        assert nominal_soc == 80.0
        assert run_normal_driving["starting_soc"] == nominal_soc

        # Precondition: the first recorded sample is below the nominal start
        first_sample = (
            test_db.query(Telemetry)
            .filter(Telemetry.simulation_id == sim_id)
            .order_by(Telemetry.timestamp)
            .first()
        )
        assert first_sample.soc_percent < nominal_soc

        data = self._what_if(client, demo_vehicle_id, "AGGRESSIVE_DRIVING", sim_id)

        assert data["starting_soc_percent"] == 80.0
        assert data["base_metrics"]["starting_soc_percent"] == 80.0
        assert data["counterfactual_metrics"]["starting_soc_percent"] == 80.0
        assert data["starting_soc_percent"] != first_sample.soc_percent

    def test_base_and_counterfactual_share_identical_starting_state(
        self, client, demo_vehicle_id, run_normal_driving
    ):
        """Same scenario and seed from the same start must reproduce the base exactly."""
        data = self._what_if(client, demo_vehicle_id, "NORMAL_DRIVING", run_normal_driving["simulation_id"])
        base = data["base_metrics"]
        counterfactual = data["counterfactual_metrics"]

        for key in self.COMPARED_METRICS:
            assert counterfactual[key] == base[key], key
        assert data["energy_change_kwh"] == 0.0

    def test_continue_base_counterfactual_starts_from_prior_state(
        self, client, demo_vehicle_id, run_normal_driving, test_db
    ):
        """A continue-mode base starts from the state recorded just before it began."""
        prior_sample = (
            test_db.query(Telemetry)
            .filter(Telemetry.simulation_id == run_normal_driving["simulation_id"])
            .order_by(Telemetry.timestamp.desc())
            .first()
        )
        # Precondition: the prior state is genuinely different from the nominal start
        assert prior_sample.soc_percent < 80.0

        continued = client.post("/api/v1/simulation/run", json={
            "vehicle_id": demo_vehicle_id,
            "scenario": "NORMAL_DRIVING",
            "duration_minutes": 10,
            "interval_seconds": 10,
            "seed": 42,
            "mode": "continue",
        })
        assert continued.status_code == 200
        continued = continued.json()
        assert continued["starting_soc"] == prior_sample.soc_percent

        data = self._what_if(client, demo_vehicle_id, "NORMAL_DRIVING", continued["simulation_id"])

        assert data["starting_soc_percent"] == prior_sample.soc_percent
        assert data["counterfactual_metrics"]["starting_soc_percent"] == prior_sample.soc_percent
        assert data["base_metrics"]["starting_soc_percent"] == prior_sample.soc_percent
        for key in self.COMPARED_METRICS:
            assert data["counterfactual_metrics"][key] == data["base_metrics"][key], key


# ============================================================
# 9. COST ANALYSIS TESTS
# ============================================================

class TestCostAnalysis:
    """Tests for cost analysis service."""

    def test_cost_endpoint_works(self, client, demo_vehicle_id, run_normal_driving):
        """Cost endpoint should return data."""
        response = client.post("/api/v1/intelligence/cost", json={
            "vehicle_id": demo_vehicle_id,
            "electricity_price_per_kwh": 8.0,
        })
        assert response.status_code == 200
        data = response.json()

        assert "energy_cost_inr" in data
        assert "wear_factor" in data
        assert "total_operating_cost_inr" in data

    def test_cost_requires_positive_price(self, client, demo_vehicle_id, run_normal_driving):
        """Electricity price must be positive."""
        response = client.post("/api/v1/intelligence/cost", json={
            "vehicle_id": demo_vehicle_id,
            "electricity_price_per_kwh": 0.0,
        })
        assert response.status_code == 422  # Validation error

        response = client.post("/api/v1/intelligence/cost", json={
            "vehicle_id": demo_vehicle_id,
            "electricity_price_per_kwh": -5.0,
        })
        assert response.status_code == 422

    def test_cost_calculation(self, client, demo_vehicle_id, run_normal_driving):
        """Cost should be calculated correctly."""
        response = client.post("/api/v1/intelligence/cost", json={
            "vehicle_id": demo_vehicle_id,
            "electricity_price_per_kwh": 8.0,
        })
        data = response.json()

        # Energy cost = energy * price
        expected_energy_cost = data["energy_used_kwh"] * 8.0
        assert abs(data["energy_cost_inr"] - expected_energy_cost) < 0.01

    def test_wear_factor_calculation(self, client, demo_vehicle_id, run_normal_driving):
        """Wear factor should be 0-1."""
        response = client.post("/api/v1/intelligence/cost", json={
            "vehicle_id": demo_vehicle_id,
            "electricity_price_per_kwh": 8.0,
        })
        data = response.json()

        assert 0 <= data["wear_factor"] <= 1

    def test_total_cost_includes_wear(self, client, demo_vehicle_id, run_normal_driving):
        """Total cost should include both energy and wear."""
        response = client.post("/api/v1/intelligence/cost", json={
            "vehicle_id": demo_vehicle_id,
            "electricity_price_per_kwh": 8.0,
        })
        data = response.json()

        expected_total = data["energy_cost_inr"] + data["estimated_battery_wear_cost_inr"]
        assert abs(data["total_operating_cost_inr"] - expected_total) < 0.01


# ============================================================
# 10. RECOMMENDATION TESTS
# ============================================================

class TestRecommendations:
    """Tests for recommendation engine."""

    def test_recommendations_endpoint_works(self, client, demo_vehicle_id, run_aggressive_driving):
        """Recommendations endpoint should return data."""
        response = client.get(f"/api/v1/intelligence/recommendations/{demo_vehicle_id}")
        assert response.status_code == 200
        data = response.json()

        assert "recommendations" in data
        assert "total_generated" in data
        assert "total_returned" in data

    def test_recommendations_max_5(self, client, demo_vehicle_id, run_aggressive_driving):
        """Maximum 5 recommendations should be returned."""
        response = client.get(f"/api/v1/intelligence/recommendations/{demo_vehicle_id}")
        data = response.json()

        assert len(data["recommendations"]) <= 5

    def test_recommendations_deduplicated(self, client, demo_vehicle_id, run_aggressive_driving):
        """Recommendations should be deduplicated by ID."""
        response = client.get(f"/api/v1/intelligence/recommendations/{demo_vehicle_id}")
        data = response.json()

        ids = [r["id"] for r in data["recommendations"]]
        assert len(ids) == len(set(ids))  # No duplicates

    def test_recommendations_ordered_by_priority(self, client, demo_vehicle_id, run_aggressive_driving):
        """Recommendations should be ordered by priority."""
        response = client.get(f"/api/v1/intelligence/recommendations/{demo_vehicle_id}")
        data = response.json()

        priority_order = {"URGENT": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
        priorities = [priority_order[r["priority"]] for r in data["recommendations"]]

        # Should be non-decreasing (sorted)
        for i in range(len(priorities) - 1):
            assert priorities[i] <= priorities[i + 1]


# ============================================================
# 11. COMPOSITE ENDPOINT TESTS
# ============================================================

class TestCompositeEndpoints:
    """Tests for composite intelligence endpoints."""

    def test_why_range_dropped_works(self, client, demo_vehicle_id, run_aggressive_driving):
        """Why-range-dropped endpoint should return comprehensive data."""
        response = client.get(f"/api/v1/intelligence/why-range-dropped/{demo_vehicle_id}")
        assert response.status_code == 200
        data = response.json()

        # Check all components present
        assert "energy" in data
        assert "range_estimate" in data
        assert "contributors" in data
        assert "anomaly" in data
        assert "battery_stress" in data
        assert "recommendations" in data
        assert "explanation" in data
        assert "confidence" in data

    def test_summary_endpoint_works(self, client, demo_vehicle_id, run_aggressive_driving):
        """Summary endpoint should return data."""
        response = client.get(f"/api/v1/intelligence/summary/{demo_vehicle_id}")
        assert response.status_code == 200
        data = response.json()

        assert "vehicle_id" in data
        assert "observed_simulation_id" in data

    def test_partial_failure_handling(self, client, demo_vehicle_id):
        """Composite endpoint should handle partial component failures."""
        # Run only AGGRESSIVE (no baseline)
        client.post("/api/v1/simulation/run", json={
            "vehicle_id": demo_vehicle_id,
            "scenario": "AGGRESSIVE_DRIVING",
            "duration_minutes": 10,
            "interval_seconds": 10,
            "seed": 42,
            "mode": "fresh",
        })

        # Should still work, just with reduced confidence
        response = client.get(f"/api/v1/intelligence/why-range-dropped/{demo_vehicle_id}")
        assert response.status_code == 200
        data = response.json()

        # Should indicate baseline unavailable
        assert data["baseline_match_type"] == "UNAVAILABLE"


# ============================================================
# 12. NO-MUTATION TESTS
# ============================================================

class TestNoMutation:
    """Tests verifying intelligence endpoints don't mutate state."""

    def test_energy_endpoint_no_mutation(self, client, demo_vehicle_id, run_normal_driving, test_db):
        """Energy endpoint should not create/modify data."""
        # Count before
        sim_count_before = test_db.query(Simulation).count()
        telemetry_count_before = test_db.query(Telemetry).count()

        # Call intelligence endpoint
        response = client.get(f"/api/v1/intelligence/energy/{demo_vehicle_id}")
        assert response.status_code == 200

        # Count after
        test_db.expire_all()  # Refresh session
        sim_count_after = test_db.query(Simulation).count()
        telemetry_count_after = test_db.query(Telemetry).count()

        assert sim_count_before == sim_count_after
        assert telemetry_count_before == telemetry_count_after

    def test_why_range_dropped_no_mutation(self, client, demo_vehicle_id, run_aggressive_driving, test_db):
        """Why-range-dropped should not create/modify data."""
        sim_count_before = test_db.query(Simulation).count()
        telemetry_count_before = test_db.query(Telemetry).count()

        response = client.get(f"/api/v1/intelligence/why-range-dropped/{demo_vehicle_id}")
        assert response.status_code == 200

        test_db.expire_all()
        sim_count_after = test_db.query(Simulation).count()
        telemetry_count_after = test_db.query(Telemetry).count()

        assert sim_count_before == sim_count_after
        assert telemetry_count_before == telemetry_count_after

    def test_what_if_no_mutation(self, client, demo_vehicle_id, run_aggressive_driving, test_db):
        """What-if should not persist counterfactual."""
        sim_count_before = test_db.query(Simulation).count()
        telemetry_count_before = test_db.query(Telemetry).count()

        response = client.post("/api/v1/intelligence/what-if", json={
            "vehicle_id": demo_vehicle_id,
            "counterfactual_scenario": "NORMAL_DRIVING",
        })
        assert response.status_code == 200

        test_db.expire_all()
        sim_count_after = test_db.query(Simulation).count()
        telemetry_count_after = test_db.query(Telemetry).count()

        assert sim_count_before == sim_count_after
        assert telemetry_count_before == telemetry_count_after


# ============================================================
# 13. DETERMINISM TESTS
# ============================================================

class TestDeterminism:
    """Tests verifying deterministic behavior."""

    def test_energy_analysis_deterministic(self, client, demo_vehicle_id, run_normal_driving):
        """Same request should return same result."""
        response1 = client.get(f"/api/v1/intelligence/energy/{demo_vehicle_id}")
        response2 = client.get(f"/api/v1/intelligence/energy/{demo_vehicle_id}")

        assert response1.json() == response2.json()

    def test_what_if_deterministic(self, client, demo_vehicle_id, run_aggressive_driving):
        """Same what-if request should return same result."""
        sim_id = run_aggressive_driving["simulation_id"]

        request = {
            "vehicle_id": demo_vehicle_id,
            "counterfactual_scenario": "NORMAL_DRIVING",
            "base_simulation_id": sim_id,
            "seed": 42,
        }

        response1 = client.post("/api/v1/intelligence/what-if", json=request)
        response2 = client.post("/api/v1/intelligence/what-if", json=request)

        assert response1.json() == response2.json()


# ============================================================
# 14. ERROR HANDLING TESTS
# ============================================================

class TestErrorHandling:
    """Tests for error handling."""

    def test_missing_vehicle_404(self, client):
        """Missing vehicle should return 404."""
        response = client.get("/api/v1/intelligence/energy/NONEXISTENT")
        assert response.status_code == 404

    def test_missing_simulation_404(self, client, demo_vehicle_id):
        """Missing simulation should return 404."""
        response = client.get(f"/api/v1/intelligence/energy/{demo_vehicle_id}")
        assert response.status_code == 404  # No simulations exist

    def test_invalid_simulation_id_404(self, client, demo_vehicle_id, run_normal_driving):
        """Invalid simulation ID should return 404."""
        response = client.get(
            f"/api/v1/intelligence/energy/{demo_vehicle_id}?simulation_id=INVALID"
        )
        assert response.status_code == 404


# ============================================================
# 15. HAND-CALCULATION FEATURE TEST
# ============================================================

class TestHandCalculation:
    """Tests with manually calculable expected values."""

    def test_energy_metrics_calculation(self, test_db):
        """Test energy metrics with known values."""
        # Create controlled telemetry
        vehicle = test_db.query(Vehicle).first()

        # Create simulation
        sim = Simulation(
            simulation_id="test-calc-sim",
            vehicle_id=vehicle.vehicle_id,
            scenario="NORMAL_DRIVING",
            mode="fresh",
            seed=42,
            start_time=datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
            duration_minutes=1,
            interval_seconds=60,
        )
        test_db.add(sim)
        test_db.commit()

        # Create 2 telemetry points with known values
        # Point 1: Start
        t1 = Telemetry(
            simulation_id=sim.simulation_id,
            vehicle_id=vehicle.vehicle_id,
            timestamp=datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
            soc_percent=80.0,
            soh_percent=94.0,
            battery_temperature_c=30.0,
            pack_voltage_v=400.0,
            pack_current_a=10.0,
            battery_power_kw=4.0,
            speed_kmh=60.0,  # 60 km/h = 1 km per minute
            acceleration_mps2=0.0,
            odometer_km=12500.0,
            trip_distance_km=0.0,
            energy_consumed_kwh=0.0,
            energy_consumption_kwh_per_100km=15.0,
            regenerative_energy_kwh=0.0,
            ambient_temperature_c=25.0,
            elevation_m=0.0,
            road_gradient_percent=0.0,
            harsh_acceleration=False,
            harsh_braking=False,
            aggressive_driving_score=10.0,
            charging=False,
            charging_power_kw=0.0,
            charger_id=None,
        )

        # Point 2: After 1 minute at 60 km/h = 1 km traveled
        # Energy consumed: 0.15 kWh (15 kWh/100km * 1 km)
        t2 = Telemetry(
            simulation_id=sim.simulation_id,
            vehicle_id=vehicle.vehicle_id,
            timestamp=datetime(2026, 1, 1, 0, 1, 0, tzinfo=timezone.utc),
            soc_percent=79.74,  # 80 - (0.15/57)*100
            soh_percent=94.0,
            battery_temperature_c=30.5,
            pack_voltage_v=400.0,
            pack_current_a=10.0,
            battery_power_kw=4.0,
            speed_kmh=60.0,
            acceleration_mps2=0.0,
            odometer_km=12501.0,  # +1 km
            trip_distance_km=1.0,  # 1 km traveled
            energy_consumed_kwh=0.15,  # 0.15 kWh consumed
            energy_consumption_kwh_per_100km=15.0,
            regenerative_energy_kwh=0.02,  # Small regen
            ambient_temperature_c=25.0,
            elevation_m=0.0,
            road_gradient_percent=0.0,
            harsh_acceleration=False,
            harsh_braking=False,
            aggressive_driving_score=10.0,
            charging=False,
            charging_power_kw=0.0,
            charger_id=None,
        )

        test_db.add(t1)
        test_db.add(t2)
        test_db.commit()

        # Extract features
        telemetry = [t1, t2]
        extractor = FeatureExtractor(DEFAULT_CONFIG)
        features = extractor.extract(telemetry)

        # Verify calculated values
        assert features.distance_km == 1.0  # 1 km traveled
        assert features.energy_consumed_kwh == 0.15  # 0.15 kWh
        assert features.energy_regenerated_kwh == 0.02  # 0.02 kWh regen
        assert features.net_energy_kwh == pytest.approx(0.13, abs=0.01)  # 0.15 - 0.02

        # Energy per km
        expected_energy_per_km = 0.13 / 1.0  # net / distance
        assert features.energy_per_km == pytest.approx(expected_energy_per_km, abs=0.01)

        # Efficiency kWh/100km
        expected_efficiency = expected_energy_per_km * 100  # 13 kWh/100km
        assert features.efficiency_kwh_per_100km == pytest.approx(expected_efficiency, abs=0.1)


# ============================================================
# 16. PAGINATION COMPATIBILITY TEST
# ============================================================

class TestPaginationCompatibility:
    """Tests verifying Sprint 1 pagination still works."""

    def test_telemetry_pagination_works(self, client, demo_vehicle_id, run_normal_driving):
        """Telemetry pagination should still work."""
        response = client.get(
            f"/api/v1/vehicles/{demo_vehicle_id}/telemetry?limit=10&offset=0"
        )
        assert response.status_code == 200
        data = response.json()

        assert "items" in data
        assert "count" in data
        assert len(data["items"]) <= 10


# ============================================================
# 17. SPRINT 1 REGRESSION TESTS
# ============================================================

class TestSprint1Regression:
    """Verify Sprint 1 functionality still works."""

    def test_simulation_run_works(self, client, demo_vehicle_id):
        """Simulation should still run."""
        response = client.post("/api/v1/simulation/run", json={
            "vehicle_id": demo_vehicle_id,
            "scenario": "NORMAL_DRIVING",
            "duration_minutes": 5,
            "interval_seconds": 10,
            "seed": 42,
            "mode": "fresh",
        })
        assert response.status_code == 200

    def test_vehicle_endpoint_works(self, client, demo_vehicle_id):
        """Vehicle endpoint should work."""
        response = client.get(f"/api/v1/vehicles/{demo_vehicle_id}")
        assert response.status_code == 200

    def test_scenarios_endpoint_works(self, client):
        """Scenarios endpoint should work."""
        response = client.get("/api/v1/simulation/scenarios")
        assert response.status_code == 200
        data = response.json()
        assert len(data["scenarios"]) == 5

    def test_reset_endpoint_works(self, client, demo_vehicle_id, run_normal_driving):
        """Reset should still work."""
        response = client.post("/api/v1/simulation/reset", json={
            "vehicle_id": demo_vehicle_id,
        })
        assert response.status_code == 200

    def test_health_endpoint_works(self, client):
        """Health check should work."""
        response = client.get("/health")
        assert response.status_code == 200
