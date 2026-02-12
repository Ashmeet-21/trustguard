"""Tests for the LivenessDetector core module."""

import numpy as np
import pytest
from PIL import Image

from backend.core.liveness_detector import LivenessDetector


@pytest.fixture(scope="module")
def detector():
    """Initialize detector once for all tests in this module."""
    return LivenessDetector()


def _make_face_like_image():
    """Create a synthetic image with skin-like colors (not a real face, but exercises the pipeline)."""
    img = np.zeros((200, 200, 3), dtype=np.uint8)
    # Skin-tone-ish background
    img[:, :] = [140, 170, 210]  # BGR light skin tone
    # Add some texture variation
    noise = np.random.randint(-20, 20, img.shape, dtype=np.int16)
    img = np.clip(img.astype(np.int16) + noise, 0, 255).astype(np.uint8)
    return img


def test_detector_initializes(detector):
    """LivenessDetector should initialize without errors."""
    assert detector is not None
    assert detector.threshold == 0.7


def test_detect_from_numpy_array(detector):
    """Should accept a numpy array and return correct structure."""
    img = _make_face_like_image()
    result = detector.detect_liveness(img)

    assert "is_live" in result
    assert "liveness_score" in result
    assert "checks" in result
    assert "risk_level" in result
    assert "classification" in result

    assert isinstance(result["is_live"], bool)
    assert 0.0 <= result["liveness_score"] <= 1.0
    assert result["classification"] in ("LIVE", "SPOOF")
    assert result["risk_level"] in ("LOW", "MEDIUM", "HIGH", "CRITICAL")


def test_detect_from_pil_image(detector):
    """Should accept a PIL Image and return correct structure."""
    pil_img = Image.fromarray(np.random.randint(0, 255, (150, 150, 3), dtype=np.uint8))
    result = detector.detect_liveness(pil_img)

    assert "is_live" in result
    assert "liveness_score" in result
    assert "checks" in result


def test_detect_invalid_input(detector):
    """Should raise ValueError on nonexistent file."""
    with pytest.raises(ValueError, match="Could not read image"):
        detector.detect_liveness("nonexistent_file.jpg")


def test_detect_invalid_type(detector):
    """Should raise ValueError on non-image input."""
    with pytest.raises(ValueError, match="Invalid image input type"):
        detector.detect_liveness(12345)


def test_all_checks_return_scores(detector):
    """All individual check scores should be between 0 and 1."""
    img = _make_face_like_image()
    result = detector.detect_liveness(img)

    checks = result["checks"]
    assert isinstance(checks["face_detected"], bool)

    for key in ["texture_score", "frequency_score", "color_score", "edge_score", "sharpness_score"]:
        assert key in checks, f"Missing check: {key}"
        assert 0.0 <= checks[key] <= 1.0, f"{key} out of range: {checks[key]}"


def test_risk_level_mapping(detector):
    """Risk levels should map correctly from liveness scores."""
    assert detector._get_risk_level(0.9) == "LOW"
    assert detector._get_risk_level(0.7) == "MEDIUM"
    assert detector._get_risk_level(0.5) == "HIGH"
    assert detector._get_risk_level(0.2) == "CRITICAL"
