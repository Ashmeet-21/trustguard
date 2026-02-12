"""Tests for the DeepfakeDetector class."""

import pytest
import numpy as np
from PIL import Image
from backend.core.deepfake_detector import DeepfakeDetector


@pytest.fixture(scope="module")
def detector():
    """Initialize detector once for all tests (it's slow to load)."""
    return DeepfakeDetector(device="cpu")


def test_detector_initializes(detector):
    """Detector should initialize successfully on CPU."""
    assert detector is not None
    assert detector.device.type == "cpu"
    assert detector.model is not None


def test_predict_from_pil_image(detector):
    """Should accept a PIL Image and return proper result dict."""
    # Create a random 224x224 image
    image = Image.fromarray(np.random.randint(0, 255, (224, 224, 3), dtype=np.uint8))
    result = detector.predict_image(image)

    assert "is_deepfake" in result
    assert isinstance(result["is_deepfake"], bool)
    assert 0.0 <= result["confidence"] <= 1.0
    assert result["classification"] in ("REAL", "FAKE")
    assert result["risk_level"] in ("LOW", "MEDIUM", "HIGH", "CRITICAL")
    assert "real" in result["probabilities"]
    assert "fake" in result["probabilities"]


def test_predict_from_numpy_array(detector):
    """Should accept a numpy array and return results."""
    image_array = np.random.randint(0, 255, (224, 224, 3), dtype=np.uint8)
    result = detector.predict_image(image_array)

    assert "is_deepfake" in result
    assert "confidence" in result


def test_predict_invalid_input(detector):
    """Should raise ValueError for non-image input."""
    with pytest.raises(ValueError):
        detector.predict_image(12345)


def test_risk_level_critical(detector):
    """0.8+ fake probability = CRITICAL."""
    assert detector._get_risk_level(0.9) == "CRITICAL"
    assert detector._get_risk_level(0.8) == "CRITICAL"


def test_risk_level_high(detector):
    """0.6-0.8 fake probability = HIGH."""
    assert detector._get_risk_level(0.7) == "HIGH"
    assert detector._get_risk_level(0.6) == "HIGH"


def test_risk_level_medium(detector):
    """0.4-0.6 fake probability = MEDIUM."""
    assert detector._get_risk_level(0.5) == "MEDIUM"
    assert detector._get_risk_level(0.4) == "MEDIUM"


def test_risk_level_low(detector):
    """Below 0.4 = LOW."""
    assert detector._get_risk_level(0.3) == "LOW"
    assert detector._get_risk_level(0.1) == "LOW"


def test_batch_predict_empty(detector):
    """Batch predict with empty list should return empty list."""
    results = detector.batch_predict([])
    assert results == []
