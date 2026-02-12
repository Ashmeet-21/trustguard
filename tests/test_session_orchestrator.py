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
