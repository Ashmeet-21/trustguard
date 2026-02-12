"""Tests for liveness detection API endpoints."""

import io
import numpy as np
from PIL import Image


def _make_test_image() -> bytes:
    """Create a small valid JPEG image in memory."""
    img = Image.fromarray(np.random.randint(0, 255, (100, 100, 3), dtype=np.uint8))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    buf.seek(0)
    return buf.read()


def test_liveness_image_success(client):
    """Should analyze liveness on a valid image upload."""
    image_bytes = _make_test_image()
    response = client.post(
        "/api/v1/detect/liveness",
        files={"file": ("test.jpg", image_bytes, "image/jpeg")},
    )
    assert response.status_code == 200

    data = response.json()
    assert "is_live" in data
    assert "liveness_score" in data
    assert "checks" in data
    assert "risk_level" in data
    assert "classification" in data
    assert "processing_time_ms" in data

    # Check structure of checks dict
    checks = data["checks"]
    assert "face_detected" in checks
    assert "texture_score" in checks
    assert "frequency_score" in checks
    assert "color_score" in checks
    assert "edge_score" in checks
    assert "sharpness_score" in checks


def test_liveness_image_wrong_type(client):
    """Should reject non-image file types."""
    response = client.post(
        "/api/v1/detect/liveness",
        files={"file": ("test.txt", b"not an image", "text/plain")},
    )
    assert response.status_code == 400


def test_liveness_image_png(client):
    """Should accept PNG images too."""
    img = Image.fromarray(np.random.randint(0, 255, (100, 100, 3), dtype=np.uint8))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)

    response = client.post(
        "/api/v1/detect/liveness",
        files={"file": ("test.png", buf.read(), "image/png")},
    )
    assert response.status_code == 200
    assert "is_live" in response.json()


def test_liveness_stub_removed(client):
    """The old stub should be replaced — liveness now requires a file upload."""
    # POST with no file should fail (422 validation error), not return "coming soon"
    response = client.post("/api/v1/detect/liveness")
    assert response.status_code == 422  # FastAPI validation error for missing file
