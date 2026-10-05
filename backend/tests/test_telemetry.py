"""Tests for telemetry endpoints."""
import pytest
from datetime import datetime, timezone


class TestTelemetryEndpoints:
    """Tests for telemetry API endpoints."""

    def test_telemetry_returns_newest_first(self, client, demo_vehicle_id):
        """Test 6: Telemetry is returned newest-first."""
        # First run a simulation to generate telemetry
        sim_request = {
            "vehicle_id": demo_vehicle_id,
            "scenario": "NORMAL_DRIVING",
            "duration_minutes": 5,
            "interval_seconds": 60,
            "seed": 42,
            "mode": "fresh",
        }
        sim_response = client.post("/api/v1/simulation/run", json=sim_request)
        assert sim_response.status_code == 200

        # Get telemetry
        response = client.get(f"/api/v1/vehicles/{demo_vehicle_id}/telemetry")

        assert response.status_code == 200
        data = response.json()

        assert "items" in data
        items = data["items"]
        assert len(items) > 0

        # Verify newest-first ordering
        timestamps = [item["timestamp"] for item in items]
        for i in range(len(timestamps) - 1):
            assert timestamps[i] >= timestamps[i + 1], "Telemetry should be newest-first"

    def test_telemetry_time_filtering(self, client, demo_vehicle_id):
        """Test 7: Telemetry time filtering works."""
        # Run simulation with known start time
        start_time = "2026-01-01T00:00:00Z"
        sim_request = {
            "vehicle_id": demo_vehicle_id,
            "scenario": "NORMAL_DRIVING",
            "duration_minutes": 10,
            "interval_seconds": 60,
            "seed": 42,
            "mode": "fresh",
            "simulation_start_time": start_time,
        }
        sim_response = client.post("/api/v1/simulation/run", json=sim_request)
        assert sim_response.status_code == 200

        # Filter by time range
        filter_start = "2026-01-01T00:03:00Z"
        filter_end = "2026-01-01T00:07:00Z"
        response = client.get(
            f"/api/v1/vehicles/{demo_vehicle_id}/telemetry",
            params={"start_time": filter_start, "end_time": filter_end},
        )

        assert response.status_code == 200
        data = response.json()

        # All returned items should be within range
        # Parse timestamps, handling both timezone-aware and naive formats
        filter_start_dt = datetime.fromisoformat(filter_start.replace("Z", "+00:00")).replace(tzinfo=None)
        filter_end_dt = datetime.fromisoformat(filter_end.replace("Z", "+00:00")).replace(tzinfo=None)

        for item in data["items"]:
            ts_str = item["timestamp"].replace("Z", "+00:00")
            ts = datetime.fromisoformat(ts_str)
            if ts.tzinfo:
                ts = ts.replace(tzinfo=None)
            assert filter_start_dt <= ts <= filter_end_dt, \
                f"Timestamp {ts} not in range [{filter_start_dt}, {filter_end_dt}]"

    def test_telemetry_limit_and_offset(self, client, demo_vehicle_id):
        """Test 8: Telemetry limit and offset work."""
        # Run simulation
        sim_request = {
            "vehicle_id": demo_vehicle_id,
            "scenario": "NORMAL_DRIVING",
            "duration_minutes": 10,
            "interval_seconds": 30,
            "seed": 42,
            "mode": "fresh",
        }
        sim_response = client.post("/api/v1/simulation/run", json=sim_request)
        assert sim_response.status_code == 200

        # Get first page
        response1 = client.get(
            f"/api/v1/vehicles/{demo_vehicle_id}/telemetry",
            params={"limit": 5, "offset": 0},
        )
        assert response1.status_code == 200
        data1 = response1.json()
        assert len(data1["items"]) == 5
        assert data1["limit"] == 5
        assert data1["offset"] == 0

        # Get second page
        response2 = client.get(
            f"/api/v1/vehicles/{demo_vehicle_id}/telemetry",
            params={"limit": 5, "offset": 5},
        )
        assert response2.status_code == 200
        data2 = response2.json()
        assert len(data2["items"]) == 5
        assert data2["offset"] == 5

        # Pages should not overlap
        ids1 = {item["telemetry_id"] for item in data1["items"]}
        ids2 = {item["telemetry_id"] for item in data2["items"]}
        assert ids1.isdisjoint(ids2), "Paginated results should not overlap"

    def test_telemetry_unknown_vehicle_returns_404(self, client):
        """Unknown vehicle telemetry returns 404."""
        response = client.get("/api/v1/vehicles/VG-NONEXISTENT-999/telemetry")

        assert response.status_code == 404
        data = response.json()
        assert "detail" in data

    def test_telemetry_contains_simulation_id(self, client, demo_vehicle_id):
        """Test 11: Telemetry contains simulation_id."""
        sim_request = {
            "vehicle_id": demo_vehicle_id,
            "scenario": "NORMAL_DRIVING",
            "duration_minutes": 5,
            "interval_seconds": 60,
            "seed": 42,
            "mode": "fresh",
        }
        sim_response = client.post("/api/v1/simulation/run", json=sim_request)
        assert sim_response.status_code == 200
        simulation_id = sim_response.json()["simulation_id"]

        # Get telemetry
        response = client.get(f"/api/v1/vehicles/{demo_vehicle_id}/telemetry")
        data = response.json()

        # All telemetry should have simulation_id
        for item in data["items"]:
            assert "simulation_id" in item
            assert item["simulation_id"] == simulation_id
