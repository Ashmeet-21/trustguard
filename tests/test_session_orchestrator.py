"""
Tests for SessionOrchestrator — multi-agent verification sessions.
"""

import io
import os
import tempfile
import numpy as np
from PIL import Image
import pytest

from backend.core.session_orchestrator import SessionOrchestrator
from backend.core.risk_engine import RiskEngine
from backend.core.behavior_analyzer import BehaviorAnalyzer


class MockDeepfakeDetector:
    def predict_image(self, path):
        return {
            "is_deepfake": False,
            "confidence": 0.95,
            "classification": "REAL",
            "risk_level": "LOW",
            "probabilities": {"real": 0.95, "fake": 0.05},
        }


class MockLivenessDetector:
    turn_yaw = -0.3  # what the "turned" photo measures; tests change it
    front_yaw = 0.0  # what the front photo measures
    _calls = 0

    def head_yaw(self, path):
        """Called twice per session: front photo first (straight = 0.0), then the turned photo."""
        self._calls += 1
        return self.front_yaw if self._calls % 2 == 1 else self.turn_yaw

    def detect_liveness(self, path):
        return {
            "is_live": True,
            "liveness_score": 0.85,
            "classification": "LIVE",
            "risk_level": "LOW",
            "checks": {
                "face_detected": True,
                "texture_score": 0.8,
                "frequency_score": 0.9,
                "color_score": 0.85,
                "edge_score": 0.8,
                "sharpness_score": 0.85,
            },
        }


class MockVoiceDetector:
    def detect_voice(self, path):
        return {
            "is_synthetic": False,
            "confidence": 0.88,
            "human_score": 0.88,
            "synthetic_score": 0.12,
            "classification": "HUMAN",
            "risk_level": "LOW",
            "model_used": "mock",
            "processing_time_ms": 10,
        }


@pytest.fixture
def orchestrator():
    return SessionOrchestrator(
        deepfake_detector=MockDeepfakeDetector(),
        liveness_detector=MockLivenessDetector(),
        voice_detector=MockVoiceDetector(),
        behavior_analyzer=BehaviorAnalyzer(),
        risk_engine=RiskEngine(),
    )


@pytest.fixture
def test_image_path():
    """Create a temp image file."""
    img = Image.fromarray(np.random.randint(0, 255, (100, 100, 3), dtype=np.uint8))
    fd, path = tempfile.mkstemp(suffix=".jpg")
    img.save(path, format="JPEG")
    os.close(fd)
    yield path
    if os.path.exists(path):
        os.remove(path)


def test_create_session(orchestrator):
    """Should create a session with valid ID."""
    session_id = orchestrator.create_session()
    assert session_id is not None
    assert len(session_id) == 36  # UUID format


def test_get_session_state(orchestrator):
    """Should return session state."""
    session_id = orchestrator.create_session()
    state = orchestrator.get_session_state(session_id)
    assert state["status"] == "created"
    assert state["session_id"] == session_id


def test_run_with_image_only(orchestrator, test_image_path):
    """Should run deepfake + liveness with just an image."""
    session_id = orchestrator.create_session()
    result = orchestrator.run_session(session_id, image_path=test_image_path)
    assert "trust_score" in result
    assert "decision" in result
    assert result["decision"] in ("PASS", "REVIEW", "FAIL")
    assert "image_agent" in result["agents"]
    assert "video_agent" in result["agents"]


def test_run_with_all_signals(orchestrator, test_image_path):
    """Should run all agents with full input."""
    session_id = orchestrator.create_session()
    behavior_data = {
        "keystrokes": [
            {"key": "h", "timestamp_ms": 0},
            {"key": "i", "timestamp_ms": 150},
        ],
        "mouse_movements": [
            {"x": 100, "y": 100, "timestamp_ms": 0},
            {"x": 120, "y": 115, "timestamp_ms": 50},
        ],
    }
    result = orchestrator.run_session(
        session_id,
        image_path=test_image_path,
        audio_path=None,  # Skip audio — no real WAV file
        behavior_data=behavior_data,
    )
    assert result["decision"] in ("PASS", "REVIEW", "FAIL")
    assert "behavior_agent" in result["agents"]


def test_session_not_found(orchestrator):
    """Should return error for unknown session."""
    state = orchestrator.get_session_state("nonexistent-id")
    assert "error" in state


def test_session_completed_status(orchestrator, test_image_path):
    """Session status should be 'completed' after run."""
    session_id = orchestrator.create_session()
    orchestrator.run_session(session_id, image_path=test_image_path)
    state = orchestrator.get_session_state(session_id)
    assert state["status"] == "completed"
    assert state["result"] is not None


# ── Head-turn challenge (R1) ─────────────────────────────

def _turned_the_right_way(orchestrator, session_id):
    """Make the mock detector report a turn in the direction this session asked for (left = negative yaw)."""
    asked = orchestrator.get_session_state(session_id)["challenge"]
    orchestrator.liveness_detector.turn_yaw = -0.3 if asked == "left" else 0.3


def test_server_picks_challenge(orchestrator):
    assert orchestrator.get_session_state(orchestrator.create_session())["challenge"] in ("left", "right")


def test_right_direction_passes(orchestrator, test_image_path):
    sid = orchestrator.create_session()
    _turned_the_right_way(orchestrator, sid)
    result = orchestrator.run_session(sid, image_path=test_image_path, turn_image_path=test_image_path)
    assert orchestrator.get_session_state(sid)["agents"]["video_agent"]["details"]["head_turn"]["passed"]
    assert result["agents"]["video_agent"]["risk_level"] == "LOW"


def test_wrong_direction_fails(orchestrator, test_image_path):
    sid = orchestrator.create_session()
    _turned_the_right_way(orchestrator, sid)
    orchestrator.liveness_detector.turn_yaw *= -1  # turned the opposite way
    result = orchestrator.run_session(sid, image_path=test_image_path, turn_image_path=test_image_path)
    assert result["agents"]["video_agent"]["risk_level"] == "CRITICAL"
    assert result["decision"] == "FAIL"


def test_missing_turn_photo_fails(orchestrator, test_image_path):
    result = orchestrator.run_session(orchestrator.create_session(), image_path=test_image_path)
    assert result["agents"]["video_agent"]["risk_level"] == "CRITICAL"


def test_expired_challenge_fails(orchestrator, test_image_path):
    from datetime import datetime, timedelta
    sid = orchestrator.create_session()
    _turned_the_right_way(orchestrator, sid)
    orchestrator.sessions[sid]["challenge_expires_at"] = (datetime.utcnow() - timedelta(seconds=1)).isoformat()
    result = orchestrator.run_session(sid, image_path=test_image_path, turn_image_path=test_image_path)
    assert result["agents"]["video_agent"]["risk_level"] == "CRITICAL"


def test_turn_is_measured_against_front_photo(orchestrator, test_image_path):
    """Front photo reads -0.08, turned photo only +0.08: below 0.15 on its own, but a change of +0.16 -> 'right' passes."""
    sid = orchestrator.create_session()
    orchestrator.sessions[sid]["challenge"] = "right"
    orchestrator.liveness_detector._calls = 0
    orchestrator.liveness_detector.front_yaw, orchestrator.liveness_detector.turn_yaw = -0.08, 0.08
    try:
        result = orchestrator.run_session(sid, image_path=test_image_path, turn_image_path=test_image_path)
    finally:
        orchestrator.liveness_detector.front_yaw = 0.0
    assert result["agents"]["video_agent"]["risk_level"] == "LOW"
