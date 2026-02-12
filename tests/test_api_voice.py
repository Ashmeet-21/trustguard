"""
Tests for voice detection API endpoints.
"""

import io
import wave
import struct
import numpy as np
import pytest

from backend.api import routes_voice
from backend.core.voice_detector import VoiceDetector


def _make_wav_bytes(duration=1.0, freq=440, sample_rate=16000):
    """Create WAV file bytes in memory."""
    n_samples = int(sample_rate * duration)
    t = np.linspace(0, duration, n_samples, endpoint=False)
    audio = np.sin(2 * np.pi * freq * t) * 0.5
    audio += np.random.normal(0, 0.05, n_samples)
    audio = (audio * 32767).astype(np.int16)

    buf = io.BytesIO()
    with wave.open(buf, "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(audio.tobytes())
    buf.seek(0)
    return buf.read()


@pytest.fixture(autouse=True)
def setup_voice_detector():
    """Ensure voice detector is initialized for tests."""
    original = routes_voice.detector
    routes_voice.detector = VoiceDetector(hf_gateway=None)
    yield
    routes_voice.detector = original


def test_voice_detect_endpoint(client):
    """POST /api/v1/detect/voice should return voice analysis result."""
    wav_data = _make_wav_bytes()
    response = client.post(
        "/api/v1/detect/voice",
        files={"file": ("test.wav", wav_data, "audio/wav")},
    )
    assert response.status_code == 200
    data = response.json()
    assert "is_synthetic" in data
    assert "confidence" in data
    assert "classification" in data
    assert data["classification"] in ("HUMAN", "SYNTHETIC", "UNKNOWN")


def test_voice_detect_rejects_invalid_file(client):
    """Should reject non-audio files."""
    response = client.post(
        "/api/v1/detect/voice",
        files={"file": ("test.txt", b"not audio", "text/plain")},
    )
    assert response.status_code == 400


def test_voice_batch_endpoint(client):
    """POST /api/v1/detect/voice/batch should process multiple files."""
    wav1 = _make_wav_bytes()
    wav2 = _make_wav_bytes(freq=880)
    response = client.post(
        "/api/v1/detect/voice/batch",
        files=[
            ("files", ("test1.wav", wav1, "audio/wav")),
            ("files", ("test2.wav", wav2, "audio/wav")),
        ],
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total_files"] == 2
    assert len(data["results"]) == 2
    assert "summary" in data


def test_voice_response_schema(client):
    """Response should match VoiceResponse schema."""
    wav_data = _make_wav_bytes()
    response = client.post(
        "/api/v1/detect/voice",
        files={"file": ("test.wav", wav_data, "audio/wav")},
    )
    data = response.json()
    assert isinstance(data["is_synthetic"], bool)
    assert isinstance(data["confidence"], float)
    assert isinstance(data["human_score"], float)
    assert isinstance(data["synthetic_score"], float)
    assert isinstance(data["processing_time_ms"], float)
    assert data["risk_level"] in ("LOW", "MEDIUM", "HIGH", "CRITICAL")
