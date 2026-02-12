"""Tests for root and health endpoints."""


def test_root_endpoint(client):
    """Root should return the landing page HTML."""
    response = client.get("/")
    assert response.status_code == 200
    assert "TrustGuard" in response.text
    assert "/docs" in response.text


def test_health_endpoint(client):
    """Health check should return healthy status."""
    response = client.get("/health")
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "healthy"
    assert "models_loaded" in data
    assert "deepfake_detector" in data["models_loaded"]
