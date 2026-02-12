"""Tests for analytics endpoints."""


def test_analytics_summary(client):
    """Should return analytics summary with correct structure."""
    response = client.get("/api/v1/analytics/summary")
    assert response.status_code == 200

    data = response.json()
    assert "total_verifications" in data
    assert "deepfakes_caught" in data
    assert "clean_results" in data
    assert "avg_confidence" in data
    assert "avg_processing_time_ms" in data
    assert "by_type" in data
    assert "by_risk_level" in data

    # Counts should be non-negative integers
    assert data["total_verifications"] >= 0
    assert data["deepfakes_caught"] >= 0


def test_analytics_recent(client):
    """Should return a list of recent verifications."""
    response = client.get("/api/v1/analytics/recent")
    assert response.status_code == 200

    data = response.json()
    assert isinstance(data, list)


def test_analytics_recent_with_limit(client):
    """Should respect the limit parameter."""
    response = client.get("/api/v1/analytics/recent?limit=5")
    assert response.status_code == 200

    data = response.json()
    assert isinstance(data, list)
    assert len(data) <= 5


def test_analytics_recent_invalid_limit(client):
    """Should reject limit > 100."""
    response = client.get("/api/v1/analytics/recent?limit=200")
    assert response.status_code == 422  # Pydantic validation error
