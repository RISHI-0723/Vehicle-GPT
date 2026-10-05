"""Tests for health endpoint."""
import pytest


class TestHealthEndpoint:
    """Tests for the health check endpoint."""

    def test_health_endpoint_works(self, client):
        """Test 1: Health endpoint works."""
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "app_name" in data
        assert "version" in data

    def test_health_returns_app_info(self, client):
        """Health endpoint returns application information."""
        response = client.get("/health")
        data = response.json()

        assert data["app_name"] == "VehicleGPT"
        assert data["version"] == "0.1.0"
