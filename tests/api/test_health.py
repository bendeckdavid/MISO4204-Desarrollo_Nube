"""Tests for health check endpoint"""
from fastapi import status
from fastapi.testclient import TestClient


class TestHealthCheck:
    """Tests for health check endpoint"""

    def test_health_check_success(self, client: TestClient):
        """Test successful health check"""
        response = client.get("/health")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "status" in data
        assert data["status"] == "healthy"
        assert "version" in data

    def test_health_check_with_db(self, client: TestClient, db):
        """Test health check with database connection"""
        response = client.get("/health")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "healthy"
