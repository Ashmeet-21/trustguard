"""
Security regression tests — each test reproduces an attack that used to work.
"""

import io

import numpy as np
import pytest
from PIL import Image

from backend.api import routes_session
from backend.core.behavior_analyzer import BehaviorAnalyzer
from backend.core.deepfake_detector import DeepfakeDetector
from backend.core.hf_gateway import DetectorUnavailable
from backend.core.quality_gates import QualityGateChecker
from backend.core.risk_engine import RiskEngine
from backend.core.session_orchestrator import SessionOrchestrator
from tests.test_session_orchestrator import MockDeepfakeDetector, MockLivenessDetector, MockVoiceDetector


class BrokenDeepfakeDetector:
    def predict_image(self, path):
        raise DetectorUnavailable("HF API down")


def _orchestrator(deepfake=None):
    return SessionOrchestrator(
        deepfake_detector=deepfake or MockDeepfakeDetector(),
        liveness_detector=MockLivenessDetector(),
        voice_detector=MockVoiceDetector(),
        behavior_analyzer=BehaviorAnalyzer(),
        risk_engine=RiskEngine(),
    )


@pytest.fixture
def mock_session_routes():
    """Run the session API with mock detectors (fast, deterministic)."""
    original = (routes_session.orchestrator, routes_session.quality_gate_checker, routes_session.audit_reporter)
    routes_session.orchestrator = _orchestrator()
    routes_session.quality_gate_checker = QualityGateChecker()
    routes_session.audit_reporter = None
    yield
    routes_session.orchestrator, routes_session.quality_gate_checker, routes_session.audit_reporter = original


def _jpeg_bytes(seed=0):
    rng = np.random.default_rng(seed)
    buf = io.BytesIO()
    Image.fromarray(rng.integers(0, 255, (64, 64, 3), dtype=np.uint8)).save(buf, format="JPEG")
    return buf.getvalue()


# ── Uploads ──────────────────────────────────────────────

def test_upload_with_fake_content_type_is_rejected(client):
    """A text file labelled image/jpeg must be rejected by the magic-byte check."""
    response = client.post(
        "/api/v1/detect/liveness",
        files={"file": ("evil.jpg", b"#!/bin/sh\necho not an image", "image/jpeg")},
    )
    assert response.status_code == 400
    assert "not a valid image" in response.json()["detail"]


def test_session_upload_size_limit(client, mock_session_routes, monkeypatch):
    """Session uploads must respect MAX_UPLOAD_SIZE like every other endpoint."""
    from backend.utils import config
    monkeypatch.setattr(config, "MAX_UPLOAD_SIZE", 1000)
    session_id = client.post("/api/v1/session/create").json()["session_id"]
    response = client.post(
        f"/api/v1/session/{session_id}/verify",
        files={"image": ("big.jpg", _jpeg_bytes() + b"\0" * 5000, "image/jpeg")},
    )
    assert response.status_code == 413


# ── Sessions ─────────────────────────────────────────────

def test_replayed_image_fails(client, mock_session_routes):
    """Same image in a second session = replay attack -> FAIL (gates used to be ignored)."""
    image = _jpeg_bytes(seed=42)

    first = client.post("/api/v1/session/create").json()["session_id"]
    r1 = client.post(f"/api/v1/session/{first}/verify", files={"image": ("a.jpg", image, "image/jpeg")})
    assert r1.json()["decision"] == "PASS"

    second = client.post("/api/v1/session/create").json()["session_id"]
    r2 = client.post(f"/api/v1/session/{second}/verify", files={"image": ("a.jpg", image, "image/jpeg")}).json()
    assert r2["decision"] == "FAIL"
    assert {"gate": "replay_protection", "passed": False} in r2["quality_gates"]


def test_session_can_only_be_run_once(client, mock_session_routes):
    """Retrying the same session until it passes must not be possible."""
    session_id = client.post("/api/v1/session/create").json()["session_id"]
    files = lambda: {"image": ("a.jpg", _jpeg_bytes(seed=7), "image/jpeg")}
    assert client.post(f"/api/v1/session/{session_id}/verify", files=files()).status_code == 200
    assert client.post(f"/api/v1/session/{session_id}/verify", files=files()).status_code == 409


def test_users_session_is_private(client, mock_session_routes, auth_headers):
    """A session created by a logged-in user can't be read or run by anyone else."""
    session_id = client.post("/api/v1/session/create", headers=auth_headers).json()["session_id"]

    assert client.get(f"/api/v1/session/{session_id}").status_code == 404
    anon = client.post(f"/api/v1/session/{session_id}/verify", files={"image": ("a.jpg", _jpeg_bytes(1), "image/jpeg")})
    assert anon.status_code == 404
    assert client.get(f"/api/v1/session/{session_id}", headers=auth_headers).status_code == 200


# ── Fail closed ──────────────────────────────────────────

def test_deepfake_api_outage_raises_instead_of_guessing_real():
    """If the HF API is down the detector must not say 'REAL'."""
    class DownGateway:
        client = object()
        def classify_image(self, path, model):
            return [{"label": "error", "score": 0}]

    detector = DeepfakeDetector(hf_gateway=DownGateway(), backend="api")
    with pytest.raises(DetectorUnavailable):
        detector.predict_image(Image.new("RGB", (32, 32)))


def test_api_mode_reads_single_output_model():
    """CommunityForensics returns one label (LABEL_0 = fake probability) — API mode must read it right."""
    class FakeGateway:
        client = object()
        def __init__(self, score):
            self.score = score
        def classify_image(self, path, model):
            return [{"label": "LABEL_0", "score": self.score}]

    image = Image.new("RGB", (32, 32))
    fake = DeepfakeDetector(hf_gateway=FakeGateway(0.93), backend="api").predict_image(image)
    real = DeepfakeDetector(hf_gateway=FakeGateway(0.02), backend="api").predict_image(image)
    assert fake["is_deepfake"] and fake["probabilities"]["fake"] == 0.93
    assert not real["is_deepfake"] and real["risk_level"] == "LOW"


def test_gateway_does_not_retry_bad_token():
    """A 401 (bad HF token) fails at once instead of retrying with sleeps."""
    from backend.core.hf_gateway import HFGateway

    class Unauthorized(Exception):
        response = type("R", (), {"status_code": 401})()

    calls = []
    class FakeClient:
        def image_classification(self, path, model):
            calls.append(1)
            raise Unauthorized("401 Unauthorized")

    gateway = HFGateway(token="")
    gateway.client = FakeClient()
    assert gateway.classify_image("x.jpg", model="m") == [{"label": "error", "score": 0}]
    assert len(calls) == 1


def test_crashed_agent_blocks_auto_pass(tmp_path):
    """Everything else looks perfect, but the deepfake check crashed -> REVIEW, never PASS."""
    orch = _orchestrator(deepfake=BrokenDeepfakeDetector())
    img = tmp_path / "x.jpg"
    img.write_bytes(_jpeg_bytes())
    result = orch.run_session(orch.create_session(), image_path=str(img), audio_path=str(img))
    assert result["decision"] == "REVIEW"


# ── Behavior ─────────────────────────────────────────────

def test_mouse_with_identical_timestamps_is_bot():
    """Teleporting mouse (all moves at the same ms) used to score as human (NaN bug)."""
    moves = [{"x": i * 100, "y": i * 50, "timestamp_ms": 1000} for i in range(20)]
    assert BehaviorAnalyzer()._check_mouse_speed(moves) <= 0.1


def test_behavior_payload_size_is_capped(client):
    """Huge behavior payloads are rejected before any processing."""
    payload = {"mouse_movements": [{"x": 1, "y": 1, "timestamp_ms": i} for i in range(5001)]}
    assert client.post("/api/v1/detect/behavior", json=payload).status_code == 422
