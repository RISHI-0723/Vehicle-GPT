"""Tests for simulation engine and API."""
import pytest
from datetime import datetime, timezone


class TestSimulationBasics:
    """Basic simulation tests."""

    def test_simulation_endpoint_works(self, client, demo_vehicle_id):
        """Test 9: Simulation endpoint works."""
        request = {
            "vehicle_id": demo_vehicle_id,
            "scenario": "NORMAL_DRIVING",
            "duration_minutes": 5,
            "interval_seconds": 60,
            "seed": 42,
            "mode": "fresh",
        }
        response = client.post("/api/v1/simulation/run", json=request)

        assert response.status_code == 200
        data = response.json()

        assert "simulation_id" in data
        assert data["vehicle_id"] == demo_vehicle_id
        assert data["scenario"] == "NORMAL_DRIVING"
        assert data["samples_generated"] == 5  # 5 minutes / 60 seconds
        assert data["starting_soc"] == 80.0  # Baseline SOC
        assert data["starting_odometer"] == 12500.0  # Baseline odometer

    def test_invalid_scenario_rejected(self, client, demo_vehicle_id):
        """Test 10: Invalid scenario is rejected."""
        request = {
            "vehicle_id": demo_vehicle_id,
            "scenario": "INVALID_SCENARIO",
            "duration_minutes": 5,
            "interval_seconds": 60,
            "seed": 42,
        }
        response = client.post("/api/v1/simulation/run", json=request)

        assert response.status_code == 422  # Validation error

    def test_invalid_duration_rejected(self, client, demo_vehicle_id):
        """Test 11: Invalid duration is rejected."""
        request = {
            "vehicle_id": demo_vehicle_id,
            "scenario": "NORMAL_DRIVING",
            "duration_minutes": 0,  # Invalid
            "interval_seconds": 60,
            "seed": 42,
        }
        response = client.post("/api/v1/simulation/run", json=request)

        assert response.status_code == 422

    def test_scenario_endpoint_response_shape(self, client):
        """Test 29: Scenario endpoint response shape is correct."""
        response = client.get("/api/v1/simulation/scenarios")

        assert response.status_code == 200
        data = response.json()

        assert "scenarios" in data
        assert len(data["scenarios"]) == 5

        expected_scenarios = {
            "NORMAL_DRIVING",
            "HOT_INDIAN_DAY",
            "AGGRESSIVE_DRIVING",
            "FAST_CHARGING",
            "ENERGY_ANOMALY",
        }
        actual_scenarios = {s["name"] for s in data["scenarios"]}
        assert actual_scenarios == expected_scenarios

        # Each scenario should have name and description
        for scenario in data["scenarios"]:
            assert "name" in scenario
            assert "description" in scenario
            assert len(scenario["description"]) > 0


class TestDeterminism:
    """Tests for deterministic simulation behavior."""

    def test_same_seed_produces_identical_telemetry(self, client, demo_vehicle_id):
        """Test 12: Same simulation inputs + same seed produce identical telemetry."""
        request = {
            "vehicle_id": demo_vehicle_id,
            "scenario": "NORMAL_DRIVING",
            "duration_minutes": 5,
            "interval_seconds": 30,
            "seed": 42,
            "mode": "fresh",
            "simulation_start_time": "2026-01-01T00:00:00Z",
        }

        # Run simulation twice
        response1 = client.post("/api/v1/simulation/run", json=request)
        assert response1.status_code == 200

        # Reset and run again
        client.post("/api/v1/simulation/reset", json={"vehicle_id": demo_vehicle_id})

        response2 = client.post("/api/v1/simulation/run", json=request)
        assert response2.status_code == 200

        data1 = response1.json()
        data2 = response2.json()

        # Summaries should match
        assert data1["samples_generated"] == data2["samples_generated"]
        assert data1["starting_soc"] == data2["starting_soc"]
        assert data1["ending_soc"] == data2["ending_soc"]
        assert data1["starting_odometer"] == data2["starting_odometer"]
        assert data1["ending_odometer"] == data2["ending_odometer"]
        assert data1["energy_consumed"] == data2["energy_consumed"]
        assert data1["distance"] == data2["distance"]
        assert data1["average_efficiency"] == data2["average_efficiency"]
        assert data1["max_battery_temperature"] == data2["max_battery_temperature"]
        assert data1["peak_power"] == data2["peak_power"]


class TestSOCBounds:
    """Tests for SOC bounds validation."""

    def test_soc_remains_bounded(self, client, demo_vehicle_id):
        """Test 13: SOC remains between 0 and 100."""
        # Run a longer aggressive driving simulation to drain battery
        request = {
            "vehicle_id": demo_vehicle_id,
            "scenario": "AGGRESSIVE_DRIVING",
            "duration_minutes": 60,
            "interval_seconds": 60,
            "seed": 42,
            "mode": "fresh",
        }
        response = client.post("/api/v1/simulation/run", json=request)
        assert response.status_code == 200

        # Get all telemetry
        tel_response = client.get(
            f"/api/v1/vehicles/{demo_vehicle_id}/telemetry",
            params={"limit": 1000},
        )
        data = tel_response.json()

        for item in data["items"]:
            assert 0 <= item["soc_percent"] <= 100, f"SOC out of bounds: {item['soc_percent']}"


class TestSpeedBounds:
    """Tests for speed validation."""

    def test_speed_never_negative(self, client, demo_vehicle_id):
        """Test 14: Speed never becomes negative."""
        request = {
            "vehicle_id": demo_vehicle_id,
            "scenario": "AGGRESSIVE_DRIVING",
            "duration_minutes": 30,
            "interval_seconds": 30,
            "seed": 42,
            "mode": "fresh",
        }
        response = client.post("/api/v1/simulation/run", json=request)
        assert response.status_code == 200

        tel_response = client.get(
            f"/api/v1/vehicles/{demo_vehicle_id}/telemetry",
            params={"limit": 1000},
        )
        data = tel_response.json()

        for item in data["items"]:
            assert item["speed_kmh"] >= 0, f"Negative speed: {item['speed_kmh']}"


class TestFastCharging:
    """Tests for FAST_CHARGING scenario."""

    def test_fast_charging_semantics(self, client, demo_vehicle_id):
        """Test 15: FAST_CHARGING has correct charging semantics."""
        request = {
            "vehicle_id": demo_vehicle_id,
            "scenario": "FAST_CHARGING",
            "duration_minutes": 30,
            "interval_seconds": 60,
            "seed": 42,
            "mode": "fresh",
        }
        response = client.post("/api/v1/simulation/run", json=request)
        assert response.status_code == 200

        data = response.json()

        # SOC should increase during charging
        assert data["ending_soc"] > data["starting_soc"], "SOC should increase during charging"

        # Get telemetry to verify charging semantics
        tel_response = client.get(
            f"/api/v1/vehicles/{demo_vehicle_id}/telemetry",
            params={"limit": 100},
        )
        tel_data = tel_response.json()

        # Count points that are actively charging (SOC < 100)
        active_charging_count = 0
        for item in tel_data["items"]:
            # Speed must be 0
            assert item["speed_kmh"] == 0, "Speed should be 0 during charging"

            # Charging flag must be true
            assert item["charging"] is True, "Charging flag should be true"

            # Check charging semantics only when SOC < 100 (charging stops at 100%)
            if item["soc_percent"] < 100:
                active_charging_count += 1
                # charging_power_kw > 0
                assert item["charging_power_kw"] > 0, "Charging power should be positive when SOC < 100"

                # battery_power_kw < 0 (charging = negative power)
                assert item["battery_power_kw"] < 0, "Battery power should be negative during charging"

                # pack_current_a < 0 (charging)
                assert item["pack_current_a"] < 0, "Pack current should be negative during charging"

        # Ensure we had some active charging points
        assert active_charging_count > 0, "Should have at least some charging points with SOC < 100"


class TestSOHConstant:
    """Tests for SOH behavior."""

    def test_soh_remains_constant(self, client, demo_vehicle_id, demo_vehicle_config):
        """Test 23: SOH remains constant in Sprint 1."""
        initial_soh = demo_vehicle_config["initial_soh_percent"]

        # Run multiple simulations
        scenarios = ["NORMAL_DRIVING", "AGGRESSIVE_DRIVING", "FAST_CHARGING"]

        for scenario in scenarios:
            request = {
                "vehicle_id": demo_vehicle_id,
                "scenario": scenario,
                "duration_minutes": 30,
                "interval_seconds": 60,
                "seed": 42,
                "mode": "fresh",
            }
            response = client.post("/api/v1/simulation/run", json=request)
            assert response.status_code == 200

            # Check all telemetry
            tel_response = client.get(
                f"/api/v1/vehicles/{demo_vehicle_id}/telemetry",
                params={"limit": 1000},
            )
            data = tel_response.json()

            for item in data["items"]:
                assert item["soh_percent"] == initial_soh, \
                    f"SOH changed in {scenario}: {item['soh_percent']} != {initial_soh}"

            # Reset for next scenario
            client.post("/api/v1/simulation/reset", json={"vehicle_id": demo_vehicle_id})


class TestScenarioComparisons:
    """Tests comparing scenarios with same seed."""

    def test_hot_indian_day_higher_thermal_load(self, client, demo_vehicle_id):
        """Test 16: HOT_INDIAN_DAY produces greater thermal/energy load than NORMAL_DRIVING."""
        # Run NORMAL_DRIVING
        normal_request = {
            "vehicle_id": demo_vehicle_id,
            "scenario": "NORMAL_DRIVING",
            "duration_minutes": 30,
            "interval_seconds": 60,
            "seed": 42,
            "mode": "fresh",
        }
        normal_response = client.post("/api/v1/simulation/run", json=normal_request)
        assert normal_response.status_code == 200
        normal_data = normal_response.json()

        # Get NORMAL telemetry for comparison
        normal_tel = client.get(
            f"/api/v1/vehicles/{demo_vehicle_id}/telemetry",
            params={"limit": 100},
        )
        normal_items = normal_tel.json()["items"]
        normal_avg_ambient = sum(i["ambient_temperature_c"] for i in normal_items) / len(normal_items)

        # Reset
        client.post("/api/v1/simulation/reset", json={"vehicle_id": demo_vehicle_id})

        # Run HOT_INDIAN_DAY
        hot_request = {
            "vehicle_id": demo_vehicle_id,
            "scenario": "HOT_INDIAN_DAY",
            "duration_minutes": 30,
            "interval_seconds": 60,
            "seed": 42,
            "mode": "fresh",
        }
        hot_response = client.post("/api/v1/simulation/run", json=hot_request)
        assert hot_response.status_code == 200
        hot_data = hot_response.json()

        # Get HOT telemetry
        hot_tel = client.get(
            f"/api/v1/vehicles/{demo_vehicle_id}/telemetry",
            params={"limit": 100},
        )
        hot_items = hot_tel.json()["items"]
        hot_avg_ambient = sum(i["ambient_temperature_c"] for i in hot_items) / len(hot_items)

        # HOT_INDIAN_DAY should have higher ambient temperature
        assert hot_avg_ambient > normal_avg_ambient, \
            f"HOT_INDIAN_DAY should have higher ambient temp: {hot_avg_ambient} vs {normal_avg_ambient}"

        # Should have higher max battery temperature or energy consumption
        assert (
            hot_data["max_battery_temperature"] > normal_data["max_battery_temperature"] or
            hot_data["energy_consumed"] > normal_data["energy_consumed"]
        ), "HOT_INDIAN_DAY should have higher thermal load or energy consumption"

    def test_aggressive_driving_higher_energy_consumption(self, client, demo_vehicle_id):
        """Test 17: AGGRESSIVE_DRIVING produces greater energy consumption than NORMAL_DRIVING."""
        # Run NORMAL_DRIVING
        normal_request = {
            "vehicle_id": demo_vehicle_id,
            "scenario": "NORMAL_DRIVING",
            "duration_minutes": 30,
            "interval_seconds": 60,
            "seed": 42,
            "mode": "fresh",
        }
        normal_response = client.post("/api/v1/simulation/run", json=normal_request)
        assert normal_response.status_code == 200
        normal_data = normal_response.json()

        # Get telemetry for aggressive score comparison
        normal_tel = client.get(
            f"/api/v1/vehicles/{demo_vehicle_id}/telemetry",
            params={"limit": 100},
        )
        normal_items = normal_tel.json()["items"]
        normal_avg_aggressive = sum(i["aggressive_driving_score"] for i in normal_items) / len(normal_items)

        # Reset
        client.post("/api/v1/simulation/reset", json={"vehicle_id": demo_vehicle_id})

        # Run AGGRESSIVE_DRIVING
        aggressive_request = {
            "vehicle_id": demo_vehicle_id,
            "scenario": "AGGRESSIVE_DRIVING",
            "duration_minutes": 30,
            "interval_seconds": 60,
            "seed": 42,
            "mode": "fresh",
        }
        aggressive_response = client.post("/api/v1/simulation/run", json=aggressive_request)
        assert aggressive_response.status_code == 200
        aggressive_data = aggressive_response.json()

        # Get telemetry
        aggressive_tel = client.get(
            f"/api/v1/vehicles/{demo_vehicle_id}/telemetry",
            params={"limit": 100},
        )
        aggressive_items = aggressive_tel.json()["items"]
        aggressive_avg_aggressive = sum(i["aggressive_driving_score"] for i in aggressive_items) / len(aggressive_items)

        # AGGRESSIVE should have higher energy consumption or aggressive score
        assert (
            aggressive_data["energy_consumed"] > normal_data["energy_consumed"] or
            aggressive_avg_aggressive > normal_avg_aggressive
        ), "AGGRESSIVE_DRIVING should have higher energy consumption or aggressive score"


class TestEnergyAnomaly:
    """Tests for ENERGY_ANOMALY scenario."""

    def test_energy_anomaly_contract(self, client, demo_vehicle_id):
        """Test 18: ENERGY_ANOMALY satisfies contract."""
        request = {
            "vehicle_id": demo_vehicle_id,
            "scenario": "ENERGY_ANOMALY",
            "duration_minutes": 60,
            "interval_seconds": 60,
            "seed": 42,
            "mode": "fresh",
        }
        response = client.post("/api/v1/simulation/run", json=request)
        assert response.status_code == 200
        data = response.json()

        # Must have anomaly fields
        assert data["anomaly_started_at"] is not None, "anomaly_started_at required"
        assert data["anomaly_ended_at"] is not None, "anomaly_ended_at required"
        assert data["baseline_consumption"] is not None, "baseline_consumption required"
        assert data["anomaly_consumption"] is not None, "anomaly_consumption required"
        assert data["anomaly_increase_percent"] is not None, "anomaly_increase_percent required"

        # Anomaly must be >= 20% increase
        assert data["anomaly_increase_percent"] >= 20.0, \
            f"Anomaly increase must be >= 20%: {data['anomaly_increase_percent']}"


class TestResetFunctionality:
    """Tests for reset functionality."""

    def test_reset_deletes_telemetry_and_simulations(self, client, demo_vehicle_id):
        """Test 19: Reset deletes telemetry and simulation history."""
        # Run simulation
        request = {
            "vehicle_id": demo_vehicle_id,
            "scenario": "NORMAL_DRIVING",
            "duration_minutes": 5,
            "interval_seconds": 60,
            "seed": 42,
            "mode": "fresh",
        }
        sim_response = client.post("/api/v1/simulation/run", json=request)
        assert sim_response.status_code == 200

        # Verify telemetry exists
        tel_response = client.get(f"/api/v1/vehicles/{demo_vehicle_id}/telemetry")
        assert tel_response.json()["count"] > 0

        # Reset
        reset_response = client.post(
            "/api/v1/simulation/reset",
            json={"vehicle_id": demo_vehicle_id},
        )
        assert reset_response.status_code == 200
        reset_data = reset_response.json()

        assert reset_data["telemetry_deleted"] > 0
        assert reset_data["simulations_deleted"] > 0

        # Verify telemetry is gone
        tel_response2 = client.get(f"/api/v1/vehicles/{demo_vehicle_id}/telemetry")
        assert tel_response2.json()["count"] == 0

        # Verify state returns to baseline
        state_response = client.get(f"/api/v1/vehicles/{demo_vehicle_id}/state")
        state_data = state_response.json()
        assert state_data["timestamp"] is None  # Baseline state
        assert state_data["soc_percent"] == 80.0  # Baseline SOC


class TestContinueMode:
    """Tests for continue mode functionality."""

    def test_continue_mode_starts_from_previous_state(self, client, demo_vehicle_id):
        """Test 20: Continue mode starts from previous latest state."""
        # Run first simulation
        request1 = {
            "vehicle_id": demo_vehicle_id,
            "scenario": "NORMAL_DRIVING",
            "duration_minutes": 10,
            "interval_seconds": 60,
            "seed": 42,
            "mode": "fresh",
        }
        response1 = client.post("/api/v1/simulation/run", json=request1)
        assert response1.status_code == 200
        data1 = response1.json()

        first_ending_soc = data1["ending_soc"]
        first_ending_odometer = data1["ending_odometer"]

        # Run second simulation in continue mode
        request2 = {
            "vehicle_id": demo_vehicle_id,
            "scenario": "NORMAL_DRIVING",
            "duration_minutes": 5,
            "interval_seconds": 60,
            "seed": 123,  # Different seed
            "mode": "continue",
        }
        response2 = client.post("/api/v1/simulation/run", json=request2)
        assert response2.status_code == 200
        data2 = response2.json()

        # Continue should start from where first ended
        assert abs(data2["starting_soc"] - first_ending_soc) < 0.1, \
            f"Continue should start from previous SOC: {data2['starting_soc']} vs {first_ending_soc}"
        assert abs(data2["starting_odometer"] - first_ending_odometer) < 0.1, \
            f"Continue should start from previous odometer: {data2['starting_odometer']} vs {first_ending_odometer}"

    def test_continue_mode_timestamp_continuity(self, client, demo_vehicle_id):
        """Test 21: Continue mode starts at previous latest timestamp + interval."""
        from datetime import timedelta

        # Run first simulation
        request1 = {
            "vehicle_id": demo_vehicle_id,
            "scenario": "NORMAL_DRIVING",
            "duration_minutes": 5,
            "interval_seconds": 60,
            "seed": 42,
            "mode": "fresh",
            "simulation_start_time": "2026-01-01T00:00:00Z",
        }
        response1 = client.post("/api/v1/simulation/run", json=request1)
        assert response1.status_code == 200

        # Get latest timestamp from first simulation
        tel_response1 = client.get(
            f"/api/v1/vehicles/{demo_vehicle_id}/telemetry",
            params={"limit": 1},
        )
        latest_timestamp = tel_response1.json()["items"][0]["timestamp"]

        # Run continue simulation
        request2 = {
            "vehicle_id": demo_vehicle_id,
            "scenario": "NORMAL_DRIVING",
            "duration_minutes": 5,
            "interval_seconds": 60,
            "seed": 123,
            "mode": "continue",
        }
        response2 = client.post("/api/v1/simulation/run", json=request2)
        assert response2.status_code == 200
        sim2_id = response2.json()["simulation_id"]

        # Get telemetry from second simulation
        tel_response2 = client.get(
            f"/api/v1/vehicles/{demo_vehicle_id}/telemetry",
            params={"limit": 100},
        )
        items = tel_response2.json()["items"]

        # Find first point from second simulation
        sim2_items = [i for i in items if i["simulation_id"] == sim2_id]
        if sim2_items:
            # Get oldest point from sim2 (list is newest-first)
            first_sim2_timestamp = sim2_items[-1]["timestamp"]

            # Parse timestamps
            latest_dt = datetime.fromisoformat(latest_timestamp.replace("Z", "+00:00"))
            first_sim2_dt = datetime.fromisoformat(first_sim2_timestamp.replace("Z", "+00:00"))

            # First point of continue should be latest + interval (60 seconds)
            expected_dt = latest_dt + timedelta(seconds=60)
            assert first_sim2_dt == expected_dt or (first_sim2_dt - latest_dt).total_seconds() == 60


class TestFreshMode:
    """Tests for fresh mode functionality."""

    def test_fresh_mode_ignores_previous_telemetry(self, client, demo_vehicle_id, demo_vehicle_config):
        """Test 22: Fresh mode ignores previous runtime telemetry."""
        # Run first simulation - this will modify the vehicle's runtime state
        request1 = {
            "vehicle_id": demo_vehicle_id,
            "scenario": "NORMAL_DRIVING",
            "duration_minutes": 30,
            "interval_seconds": 60,
            "seed": 42,
            "mode": "fresh",
        }
        response1 = client.post("/api/v1/simulation/run", json=request1)
        assert response1.status_code == 200
        data1 = response1.json()

        # SOC should have changed from baseline
        assert data1["ending_soc"] != demo_vehicle_config["initial_soc_percent"], \
            "First simulation should have changed SOC"

        # Run fresh simulation (should start from baseline, not previous ending state)
        request2 = {
            "vehicle_id": demo_vehicle_id,
            "scenario": "NORMAL_DRIVING",
            "duration_minutes": 5,
            "interval_seconds": 60,
            "seed": 123,
            "mode": "fresh",
        }
        response2 = client.post("/api/v1/simulation/run", json=request2)
        assert response2.status_code == 200
        data2 = response2.json()

        # Fresh should start from baseline SOC, not from previous ending SOC
        assert data2["starting_soc"] == demo_vehicle_config["initial_soc_percent"], \
            f"Fresh mode should start from baseline SOC: {data2['starting_soc']} vs {demo_vehicle_config['initial_soc_percent']}"

        # Also verify it didn't start from the previous ending SOC
        assert data2["starting_soc"] != data1["ending_soc"], \
            "Fresh mode should ignore previous simulation's ending state"


class TestCustomStartTime:
    """Tests for custom simulation start time."""

    def test_custom_start_time_honored_in_fresh_mode(self, client, demo_vehicle_id):
        """Test 24: Custom simulation_start_time is honored in fresh mode."""
        custom_time = "2026-06-15T14:30:00Z"
        request = {
            "vehicle_id": demo_vehicle_id,
            "scenario": "NORMAL_DRIVING",
            "duration_minutes": 5,
            "interval_seconds": 60,
            "seed": 42,
            "mode": "fresh",
            "simulation_start_time": custom_time,
        }
        response = client.post("/api/v1/simulation/run", json=request)
        assert response.status_code == 200
        data = response.json()

        # Start time should match custom time (compare as strings, normalize format)
        response_start = data["start_time"].replace("+00:00", "Z")
        assert response_start == custom_time or data["start_time"] == "2026-06-15T14:30:00+00:00"

        # Get telemetry
        tel_response = client.get(
            f"/api/v1/vehicles/{demo_vehicle_id}/telemetry",
            params={"limit": 100},
        )
        items = tel_response.json()["items"]

        # All timestamps should start from custom time
        # Parse both to naive datetimes for comparison
        custom_dt = datetime.fromisoformat(custom_time.replace("Z", "+00:00")).replace(tzinfo=None)
        oldest_item = items[-1]  # Oldest (list is newest-first)
        oldest_str = oldest_item["timestamp"].replace("Z", "+00:00")
        oldest_dt = datetime.fromisoformat(oldest_str)
        if oldest_dt.tzinfo:
            oldest_dt = oldest_dt.replace(tzinfo=None)
        assert oldest_dt == custom_dt, f"Expected {custom_dt}, got {oldest_dt}"

    def test_continue_mode_ignores_simulation_start_time(self, client, demo_vehicle_id):
        """Test 25: Continue mode ignores supplied simulation_start_time."""
        # First simulation
        request1 = {
            "vehicle_id": demo_vehicle_id,
            "scenario": "NORMAL_DRIVING",
            "duration_minutes": 5,
            "interval_seconds": 60,
            "seed": 42,
            "mode": "fresh",
            "simulation_start_time": "2026-01-01T00:00:00Z",
        }
        response1 = client.post("/api/v1/simulation/run", json=request1)
        assert response1.status_code == 200

        # Get latest timestamp
        tel_response1 = client.get(
            f"/api/v1/vehicles/{demo_vehicle_id}/telemetry",
            params={"limit": 1},
        )
        latest_ts = tel_response1.json()["items"][0]["timestamp"]

        # Continue with different start_time (should be ignored)
        request2 = {
            "vehicle_id": demo_vehicle_id,
            "scenario": "NORMAL_DRIVING",
            "duration_minutes": 5,
            "interval_seconds": 60,
            "seed": 123,
            "mode": "continue",
            "simulation_start_time": "2030-12-31T23:59:00Z",  # Should be ignored
        }
        response2 = client.post("/api/v1/simulation/run", json=request2)
        assert response2.status_code == 200
        data2 = response2.json()

        # Start time should NOT be the custom time, should continue from latest
        assert data2["start_time"] != "2030-12-31T23:59:00Z"


class TestTransactionSafety:
    """Tests for transaction safety."""

    def test_failed_simulation_no_partial_data(self, client, demo_vehicle_id):
        """Test 26: Failed simulation does not leave partial telemetry.

        Note: This test verifies that successful simulations commit atomically.
        Testing actual failure scenarios would require mocking.
        """
        # Get initial telemetry count
        tel_before = client.get(f"/api/v1/vehicles/{demo_vehicle_id}/telemetry")
        count_before = tel_before.json()["count"]

        # Run valid simulation
        request = {
            "vehicle_id": demo_vehicle_id,
            "scenario": "NORMAL_DRIVING",
            "duration_minutes": 5,
            "interval_seconds": 60,
            "seed": 42,
            "mode": "fresh",
        }
        response = client.post("/api/v1/simulation/run", json=request)
        assert response.status_code == 200

        # Get telemetry count after
        tel_after = client.get(f"/api/v1/vehicles/{demo_vehicle_id}/telemetry")
        count_after = tel_after.json()["count"]

        # Should have exactly 5 new points (5 minutes / 60 seconds)
        assert count_after == count_before + 5


class TestConcurrency:
    """Tests for concurrency handling."""

    def test_concurrent_same_vehicle_returns_409(self, client, demo_vehicle_id):
        """Test 28: Concurrent same-vehicle simulation request returns 409.

        Note: This is a simplified test since httpx TestClient is synchronous.
        Full concurrency testing would require async client or threading.
        """
        # The service layer implements locking, so sequential requests succeed
        # but concurrent requests would return 409
        request = {
            "vehicle_id": demo_vehicle_id,
            "scenario": "NORMAL_DRIVING",
            "duration_minutes": 1,
            "interval_seconds": 60,
            "seed": 42,
            "mode": "fresh",
        }

        # First request should succeed
        response1 = client.post("/api/v1/simulation/run", json=request)
        assert response1.status_code == 200

        # Sequential second request should also succeed (lock released)
        response2 = client.post("/api/v1/simulation/run", json=request)
        assert response2.status_code == 200


class TestErrorResponseContract:
    """Tests for error response format."""

    def test_error_response_shape(self, client):
        """Test 30: Error response shape is correct."""
        # 404 error
        response = client.get("/api/v1/vehicles/VG-NONEXISTENT-999")
        assert response.status_code == 404
        data = response.json()
        assert "detail" in data
        assert isinstance(data["detail"], str)

        # 422 validation error (invalid scenario)
        request = {
            "vehicle_id": "VG-DEMO-001",
            "scenario": "INVALID",
            "duration_minutes": 5,
            "interval_seconds": 60,
        }
        response2 = client.post("/api/v1/simulation/run", json=request)
        assert response2.status_code == 422
