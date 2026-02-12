"""
Tests for RiskEngine — multi-signal risk scoring.
"""

import pytest
from backend.core.risk_engine import RiskEngine


@pytest.fixture
def engine():
    return RiskEngine()


def test_all_pass_scenario(engine):
    """All agents passing with high scores → PASS."""
    signals = {
        "image_agent": {"score": 90, "risk_level": "LOW"},
        "video_agent": {"score": 85, "risk_level": "LOW"},
        "voice_agent": {"score": 80, "risk_level": "LOW"},
        "behavior_agent": {"score": 88, "risk_level": "LOW"},
    }
    result = engine.calculate(signals)
    assert result["decision"] == "PASS"
    assert result["trust_score"] >= 70
    assert result["overall_risk"] == "LOW"


def test_all_fail_scenario(engine):
    """All agents failing with low scores → FAIL."""
    signals = {
        "image_agent": {"score": 10, "risk_level": "CRITICAL"},
        "video_agent": {"score": 15, "risk_level": "CRITICAL"},
        "voice_agent": {"score": 20, "risk_level": "CRITICAL"},
        "behavior_agent": {"score": 5, "risk_level": "CRITICAL"},
    }
    result = engine.calculate(signals)
    assert result["decision"] == "FAIL"
    assert result["trust_score"] < 40


def test_mixed_signals_review(engine):
    """Mixed signals → REVIEW."""
    signals = {
        "image_agent": {"score": 80, "risk_level": "LOW"},
        "video_agent": {"score": 30, "risk_level": "HIGH"},
    }
    result = engine.calculate(signals)
    assert result["decision"] in ("REVIEW", "FAIL")


def test_critical_agent_forces_fail(engine):
    """One CRITICAL agent should force FAIL even if others pass."""
    signals = {
        "image_agent": {"score": 95, "risk_level": "LOW"},
        "video_agent": {"score": 90, "risk_level": "LOW"},
        "voice_agent": {"score": 5, "risk_level": "CRITICAL"},
    }
    result = engine.calculate(signals)
    assert result["decision"] == "FAIL"


def test_missing_signals_adjusts_weights(engine):
    """Should work with subset of agents."""
    signals = {
        "image_agent": {"score": 85, "risk_level": "LOW"},
    }
    result = engine.calculate(signals)
    assert result["trust_score"] == 85.0
    assert result["decision"] == "PASS"


def test_no_signals_returns_fail(engine):
    """Empty signals → FAIL."""
    result = engine.calculate({})
    assert result["decision"] == "FAIL"
    assert result["trust_score"] == 0


def test_explanation_content(engine):
    """Explanation should describe each agent."""
    signals = {
        "image_agent": {"score": 85, "risk_level": "LOW"},
        "voice_agent": {"score": 40, "risk_level": "HIGH"},
    }
    result = engine.calculate(signals)
    assert len(result["explanation"]) == 2
    assert any("image_agent" in e for e in result["explanation"])
    assert any("voice_agent" in e for e in result["explanation"])


def test_two_high_agents_fail(engine):
    """Two HIGH-risk agents → FAIL."""
    signals = {
        "image_agent": {"score": 50, "risk_level": "HIGH"},
        "video_agent": {"score": 45, "risk_level": "HIGH"},
        "voice_agent": {"score": 80, "risk_level": "LOW"},
    }
    result = engine.calculate(signals)
    assert result["decision"] == "FAIL"
