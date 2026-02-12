"""Tests for deepfake detection API endpoints."""

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


def test_detect_image_success(client):
    """Should detect deepfake on a valid image upload."""
    image_bytes = _make_test_image()
    response = client.post(
        "/api/v1/detect/deepfake/image",
        files={"file": ("test.jpg", image_bytes, "image/jpeg")},
    )
    assert response.status_code == 200

    data = response.json()
    assert "is_deepfake" in data
    assert "confidence" in data
    assert "classification" in data
    assert "risk_level" in data
    assert "processing_time_ms" in data


def test_detect_image_wrong_type(client):
    """Should reject non-image file types."""
    response = client.post(
        "/api/v1/detect/deepfake/image",
        files={"file": ("test.txt", b"not an image", "text/plain")},
    )
    assert response.status_code == 400


def test_detect_image_png(client):
    """Should accept PNG images too."""
    img = Image.fromarray(np.random.randint(0, 255, (100, 100, 3), dtype=np.uint8))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)

    response = client.post(
        "/api/v1/detect/deepfake/image",
        files={"file": ("test.png", buf.read(), "image/png")},
    )
    assert response.status_code == 200


def test_batch_too_many_files(client):
    """Should reject batch with more than 10 files."""
    image_bytes = _make_test_image()
    files = [("files", (f"test_{i}.jpg", image_bytes, "image/jpeg")) for i in range(11)]
    response = client.post("/api/v1/detect/batch", files=files)
    assert response.status_code == 400


def test_batch_success(client):
    """Should process a batch of images successfully."""
    image_bytes = _make_test_image()
    files = [("files", (f"test_{i}.jpg", image_bytes, "image/jpeg")) for i in range(3)]
    response = client.post("/api/v1/detect/batch", files=files)
    assert response.status_code == 200

    data = response.json()
    assert data["total_files"] == 3
    assert len(data["results"]) == 3
    assert "summary" in data


