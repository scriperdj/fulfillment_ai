"""
Tests for FastAPI application
"""

import pytest
from fastapi.testclient import TestClient

from src.api import app


@pytest.fixture
def client():
    """Create test client"""
    return TestClient(app)


def test_health_check(client):
    """Test health check endpoint"""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_status(client):
    """Test status endpoint"""
    response = client.get("/status")
    assert response.status_code == 200
    assert response.json()["status"] == "ready"


def test_kpi_dashboard(client):
    """Test KPI dashboard endpoint"""
    response = client.get("/kpi/dashboard")
    assert response.status_code == 200
    assert "kpis" in response.json()


def test_list_orders(client):
    """Test list orders endpoint"""
    response = client.get("/orders")
    assert response.status_code == 200
    assert "orders" in response.json()
