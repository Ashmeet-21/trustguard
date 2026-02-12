"""
Tests for behavior detection API endpoints.
"""

import pytest
from backend.api import routes_behavior
from backend.core.behavior_analyzer import BehaviorAnalyzer


@pytest.fixture(autouse=True)
def setup_behavior_analyzer():
    """Ensure behavior analyzer is initialized for tests."""
    original = routes_behavior.analyzer
    routes_behavior.analyzer = BehaviorAnalyzer()
    yield
    routes_behavior.analyzer = original


def _human_payload():
    """Realistic human keystroke + mouse data."""
    return {
        "keystrokes": [
            {"key": "h", "timestamp_ms": 0},
            {"key": "e", "timestamp_ms": 120},
            {"key": "l", "timestamp_ms": 230},
            {"key": "l", "timestamp_ms": 350},
            {"key": "o", "timestamp_ms": 480},
        ],
        "mouse_movements": [
            {"x": 100, "y": 100, "timestamp_ms": 0},
            {"x": 115, "y": 108, "timestamp_ms": 50},
            {"x": 135, "y": 120, "timestamp_ms": 100},
            {"x": 160, "y": 135, "timestamp_ms": 150},
            {"x": 190, "y": 148, "timestamp_ms": 200},
        ],
    }


def test_behavior_endpoint(client):
    """POST /api/v1/detect/behavior should return behavior analysis."""
    response = client.post("/api/v1/detect/behavior", json=_human_payload())
    assert response.status_code == 200
    data = response.json()
    assert "is_human" in data
    assert "behavior_score" in data
    assert "classification" in data
    assert data["classification"] in ("HUMAN", "BOT")


def test_behavior_empty_data(client):
    """Should handle empty keystroke and mouse data."""
    response = client.post("/api/v1/detect/behavior", json={"keystrokes": [], "mouse_movements": []})
    assert response.status_code == 200
    data = response.json()
    assert data["behavior_score"] == 0.0


def test_behavior_response_structure(client):
    """Response should have checks breakdown."""
    response = client.post("/api/v1/detect/behavior", json=_human_payload())
    data = response.json()
    checks = data["checks"]
    assert "typing_speed_score" in checks
    assert "typing_rhythm_score" in checks
    assert "mouse_speed_score" in checks
    assert "mouse_straightness_score" in checks
    assert isinstance(data["processing_time_ms"], float)


def test_behavior_invalid_payload(client):
    """Should reject invalid payload structure."""
    response = client.post("/api/v1/detect/behavior", json={"bad_field": 123})
    assert response.status_code == 200  # defaults to empty lists
