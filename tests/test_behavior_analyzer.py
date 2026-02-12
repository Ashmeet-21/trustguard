"""
Tests for BehaviorAnalyzer — behavioral biometrics detection.
"""

import pytest
from backend.core.behavior_analyzer import BehaviorAnalyzer


@pytest.fixture
def analyzer():
    return BehaviorAnalyzer()


def _human_keystrokes():
    """Realistic human keystroke data — 100-200ms intervals with variance."""
    import random
    timestamps = [0]
    for _ in range(20):
        timestamps.append(timestamps[-1] + random.randint(80, 250))
    return [{"key": chr(97 + i % 26), "timestamp_ms": t} for i, t in enumerate(timestamps)]


def _bot_keystrokes():
    """Bot-like keystroke data — perfectly uniform 10ms intervals."""
    return [{"key": chr(97 + i % 26), "timestamp_ms": i * 10} for i in range(20)]


def _human_mouse():
    """Human-like mouse movements — curved path with varying speed."""
    import random
    movements = [{"x": 100, "y": 100, "timestamp_ms": 0}]
    for i in range(1, 15):
        movements.append({
            "x": 100 + i * 20 + random.randint(-10, 10),
            "y": 100 + i * 15 + random.randint(-8, 8),
            "timestamp_ms": i * 50 + random.randint(-10, 10),
        })
    return movements


def _bot_mouse():
    """Bot-like mouse — perfectly straight, instant movement."""
    return [
        {"x": 0, "y": 0, "timestamp_ms": 0},
        {"x": 500, "y": 500, "timestamp_ms": 1},
        {"x": 1000, "y": 1000, "timestamp_ms": 2},
    ]


def test_analyze_returns_expected_keys(analyzer):
    """Result should have all required fields."""
    result = analyzer.analyze({"keystrokes": _human_keystrokes(), "mouse_movements": _human_mouse()})
    assert "is_human" in result
    assert "behavior_score" in result
    assert "classification" in result
    assert "risk_level" in result
    assert "checks" in result


def test_human_data_scores_high(analyzer):
    """Human-like data should score above threshold."""
    result = analyzer.analyze({"keystrokes": _human_keystrokes(), "mouse_movements": _human_mouse()})
    assert result["behavior_score"] >= 0.5
    assert result["classification"] == "HUMAN"


def test_bot_data_scores_low(analyzer):
    """Bot-like data should score below threshold."""
    result = analyzer.analyze({"keystrokes": _bot_keystrokes(), "mouse_movements": _bot_mouse()})
    assert result["behavior_score"] < 0.6
    assert result["classification"] == "BOT"


def test_empty_data_scores_zero(analyzer):
    """No data should return zero score."""
    result = analyzer.analyze({"keystrokes": [], "mouse_movements": []})
    assert result["behavior_score"] == 0.0


def test_keystroke_only(analyzer):
    """Should work with keystrokes only (no mouse data)."""
    result = analyzer.analyze({"keystrokes": _human_keystrokes(), "mouse_movements": []})
    assert "behavior_score" in result
    assert result["behavior_score"] > 0


def test_risk_level_mapping(analyzer):
    """Test risk level boundaries."""
    assert analyzer._get_risk_level(0.9) == "LOW"
    assert analyzer._get_risk_level(0.7) == "MEDIUM"
    assert analyzer._get_risk_level(0.5) == "HIGH"
    assert analyzer._get_risk_level(0.2) == "CRITICAL"
