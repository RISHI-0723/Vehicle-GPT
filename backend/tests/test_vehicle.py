"""Tests for vehicle endpoints."""
import pytest

from app.core.config import DEMO_VEHICLE_CONFIG


class TestVehicleEndpoints:
    """Tests for vehicle API endpoints."""

    def test_demo_vehicle_exists(self, client, demo_vehicle_id):
        """Test 2: Demo vehicle exists."""
        response = client.get(f"/api/v1/vehicles/{demo_vehicle_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["vehicle_id"] == demo_vehicle_id

    def test_vehicle_endpoint_returns_canonical_vehicle(self, client, demo_vehicle_id, demo_vehicle_config):
        """Test 3: Vehicle endpoint returns canonical vehicle."""
        response = client.get(f"/api/v1/vehicles/{demo_vehicle_id}")

        assert response.status_code == 200
        data = response.json()

        # Verify canonical values
        assert data["vehicle_id"] == demo_vehicle_config["vehicle_id"]
        assert data["make"] == demo_vehicle_config["make"]
        assert data["model"] == demo_vehicle_config["model"]
        assert data["model_year"] == demo_vehicle_config["model_year"]
        assert data["battery_capacity_kwh"] == demo_vehicle_config["battery_capacity_kwh"]
        assert data["usable_battery_capacity_kwh"] == demo_vehicle_config["usable_battery_capacity_kwh"]
        assert data["battery_type"] == demo_vehicle_config["battery_type"]
        assert data["initial_soh_percent"] == demo_vehicle_config["initial_soh_percent"]
        assert data["initial_soc_percent"] == demo_vehicle_config["initial_soc_percent"]
        assert data["initial_battery_temperature_c"] == demo_vehicle_config["initial_battery_temperature_c"]
        assert data["initial_odometer_km"] == demo_vehicle_config["initial_odometer_km"]

    def test_vehicle_list_response_shape(self, client):
        """Test 4: Vehicle list response shape is correct."""
        response = client.get("/api/v1/vehicles")

        assert response.status_code == 200
        data = response.json()

        # Must have vehicles array and count
        assert "vehicles" in data
        assert "count" in data
        assert isinstance(data["vehicles"], list)
        assert data["count"] == len(data["vehicles"])
        assert data["count"] == 1  # Only demo vehicle

    def test_state_endpoint_works(self, client, demo_vehicle_id, demo_vehicle_config):
        """Test 5: Latest state endpoint works."""
        response = client.get(f"/api/v1/vehicles/{demo_vehicle_id}/state")

        assert response.status_code == 200
        data = response.json()

        # Should return baseline state (no telemetry yet)
        assert data["vehicle_id"] == demo_vehicle_id
        assert data["timestamp"] is None  # Baseline state
        assert data["soc_percent"] == demo_vehicle_config["initial_soc_percent"]
        assert data["soh_percent"] == demo_vehicle_config["initial_soh_percent"]
        assert data["battery_temperature_c"] == demo_vehicle_config["initial_battery_temperature_c"]
        assert data["odometer_km"] == demo_vehicle_config["initial_odometer_km"]
        assert data["speed_kmh"] == 0.0
        assert data["charging"] is False

    def test_unknown_vehicle_returns_404(self, client):
        """Test 27: Unknown vehicle returns 404."""
        response = client.get("/api/v1/vehicles/VG-NONEXISTENT-999")

        assert response.status_code == 404
        data = response.json()
        assert "detail" in data
        assert "VG-NONEXISTENT-999" in data["detail"]

    def test_unknown_vehicle_state_returns_404(self, client):
        """Unknown vehicle state returns 404."""
        response = client.get("/api/v1/vehicles/VG-NONEXISTENT-999/state")

        assert response.status_code == 404
