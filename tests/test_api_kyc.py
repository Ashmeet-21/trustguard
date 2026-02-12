"""Tests for KYC verification pipeline endpoint."""

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


def test_kyc_success(client):
    """Should return a full KYC verdict with both checks."""
    image_bytes = _make_test_image()
    response = client.post(
        "/api/v1/verify/kyc",
        files={"file": ("selfie.jpg", image_bytes, "image/jpeg")},
    )
    assert response.status_code == 200

    data = response.json()
    # Must have a verdict
    assert data["verdict"] in ("PASS", "FAIL", "REVIEW")
    assert "reason" in data
    assert "overall_risk" in data
    assert "processing_time_ms" in data

    # Must have both sub-checks
    assert "deepfake_check" in data
    assert "liveness_check" in data

    # Deepfake check structure
    df = data["deepfake_check"]
    assert "is_deepfake" in df
    assert "confidence" in df
    assert "classification" in df

    # Liveness check structure
    lv = data["liveness_check"]
    assert "is_live" in lv
    assert "liveness_score" in lv
    assert "checks" in lv


def test_kyc_wrong_file_type(client):
    """Should reject non-image files."""
    response = client.post(
        "/api/v1/verify/kyc",
        files={"file": ("doc.txt", b"not an image", "text/plain")},
    )
    assert response.status_code == 400


def test_kyc_png(client):
    """Should accept PNG images."""
    img = Image.fromarray(np.random.randint(0, 255, (100, 100, 3), dtype=np.uint8))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)

    response = client.post(
        "/api/v1/verify/kyc",
        files={"file": ("selfie.png", buf.read(), "image/png")},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["verdict"] in ("PASS", "FAIL", "REVIEW")


def test_kyc_stub_removed(client):
    """The old KYC stub should be replaced — now requires file upload."""
    response = client.post("/api/v1/verify/kyc")
    assert response.status_code == 422  # Missing required file
