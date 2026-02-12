"""
Tests for QualityGateChecker — validation rules before final decision.
"""

import os
import tempfile
import pytest
from backend.core.quality_gates import QualityGateChecker


@pytest.fixture
def checker():
    return QualityGateChecker()


def test_replay_detection_new_file(checker):
    """New file should pass replay check."""
    assert checker.check_replay("abc123hash", "session-1") is True


def test_replay_detection_same_hash(checker):
    """Same hash from different session should fail replay check."""
    checker.check_replay("abc123hash", "session-1")
    assert checker.check_replay("abc123hash", "session-2") is False


def test_replay_same_session_ok(checker):
    """Same hash from same session should pass (not a replay)."""
    checker.check_replay("abc123hash", "session-1")
    assert checker.check_replay("abc123hash", "session-1") is True


def test_minimum_signals_pass(checker):
    """2+ agents completed → pass."""
    result = {
        "agents": {
            "image_agent": {"score": 80, "risk_level": "LOW"},
            "video_agent": {"score": 75, "risk_level": "LOW"},
        }
    }
    assert checker.check_minimum_signals(result) is True


def test_minimum_signals_fail(checker):
    """Only 1 agent completed → fail."""
    result = {
        "agents": {
            "image_agent": {"score": 80, "risk_level": "LOW"},
        }
    }
    assert checker.check_minimum_signals(result) is False


def test_signal_agreement_pass(checker):
    """Agents agree → pass."""
    result = {
        "agents": {
            "image_agent": {"score": 80, "risk_level": "LOW"},
            "video_agent": {"score": 70, "risk_level": "MEDIUM"},
        }
    }
    assert checker.check_signal_agreement(result) is True


def test_signal_agreement_fail(checker):
    """Agents wildly disagree (LOW vs CRITICAL) → fail."""
    result = {
        "agents": {
            "image_agent": {"score": 90, "risk_level": "LOW"},
            "video_agent": {"score": 10, "risk_level": "CRITICAL"},
        }
    }
    assert checker.check_signal_agreement(result) is False


def test_compute_file_hash():
    """Should compute SHA256 hash of a file."""
    fd, path = tempfile.mkstemp()
    os.write(fd, b"test content for hashing")
    os.close(fd)
    try:
        hash_val = QualityGateChecker.compute_file_hash(path)
        assert len(hash_val) == 64  # SHA256 hex length
        assert hash_val == QualityGateChecker.compute_file_hash(path)  # Deterministic
    finally:
        os.remove(path)
