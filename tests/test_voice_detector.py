"""
Tests for VoiceDetector — voice deepfake detection logic.
"""

import os
import struct
import wave
import pytest
import numpy as np

from backend.core.voice_detector import VoiceDetector


def _create_test_wav(path, duration=1.0, freq=440, sample_rate=16000):
    """Create a simple WAV file with a sine wave for testing."""
    n_samples = int(sample_rate * duration)
    t = np.linspace(0, duration, n_samples, endpoint=False)
    # Add some variation to simulate human speech
    audio = np.sin(2 * np.pi * freq * t) * 0.5
    # Add noise for realism
    audio += np.random.normal(0, 0.05, n_samples)
    audio = (audio * 32767).astype(np.int16)

    with wave.open(path, "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(audio.tobytes())


@pytest.fixture
def detector():
    """VoiceDetector with no HF gateway (local-only mode)."""
    return VoiceDetector(hf_gateway=None)


@pytest.fixture
def sample_wav(tmp_path):
    """Create a temporary WAV file for testing."""
    path = str(tmp_path / "test_audio.wav")
    _create_test_wav(path, duration=2.0, freq=440)
    return path


def test_detect_voice_returns_expected_keys(detector, sample_wav):
    """Result dict should have all required fields."""
    result = detector.detect_voice(sample_wav)
    assert "is_synthetic" in result
    assert "confidence" in result
    assert "human_score" in result
    assert "synthetic_score" in result
    assert "classification" in result
    assert "risk_level" in result
    assert "model_used" in result
    assert "processing_time_ms" in result


def test_detect_voice_classification_values(detector, sample_wav):
    """Classification should be HUMAN or SYNTHETIC."""
    result = detector.detect_voice(sample_wav)
    assert result["classification"] in ("HUMAN", "SYNTHETIC", "UNKNOWN")


def test_detect_voice_confidence_range(detector, sample_wav):
    """Confidence should be between 0 and 1."""
    result = detector.detect_voice(sample_wav)
    assert 0.0 <= result["confidence"] <= 1.0


def test_detect_voice_risk_levels(detector, sample_wav):
    """Risk level should be one of the four standard levels."""
    result = detector.detect_voice(sample_wav)
    assert result["risk_level"] in ("LOW", "MEDIUM", "HIGH", "CRITICAL")


def test_detect_voice_uses_local_without_hf(detector, sample_wav):
    """Without HF gateway, should use local spectral analysis."""
    result = detector.detect_voice(sample_wav)
    assert result["model_used"] == "local_spectral"


def test_risk_level_mapping(detector):
    """Test _get_risk_level thresholds."""
    assert detector._get_risk_level(0.9) == "CRITICAL"
    assert detector._get_risk_level(0.7) == "HIGH"
    assert detector._get_risk_level(0.5) == "MEDIUM"
    assert detector._get_risk_level(0.2) == "LOW"
