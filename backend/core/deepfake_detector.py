"""
Deepfake Detector Module

API mode (HF_TOKEN set):   calls HF Inference API — no torch needed, works on 512MB RAM
Local mode (no HF_TOKEN):  runs the same model locally with transformers (dev/local only)

Model: config.HF_IMAGE_MODEL — default buildborderless/CommunityForensics-DeepfakeDet-ViT.
Chosen by benchmarks/run_benchmark.py --compare: best of 8 models on fakes it had never seen
(AUC 0.88, 0% real photos wrongly flagged). See benchmarks/MODEL_COMPARISON.md.
"""

import tempfile
import os
import numpy as np
from PIL import Image
from loguru import logger
from typing import Dict, Union
import cv2

from backend.core.hf_gateway import DetectorUnavailable
from backend.utils import config

# Models name their classes differently — any of these labels means "not a real photo".
# (CommunityForensics has a single output, LABEL_0 = probability the image is fake.)
FAKE_LABELS = {"fake", "deepfake", "ai", "artificial", "label_0"}


class DeepfakeDetector:
    """
    Deepfake Detection using a pretrained Vision Transformer (ViT).

    In production (HF_TOKEN set), inference goes through the HF Inference API.
    Locally, it runs the model with transformers for offline use.
    """

    def __init__(self, device: str = None, hf_gateway=None, model_name: str = None):
        self.model_name = model_name or config.HF_IMAGE_MODEL
        self._hf_gateway = hf_gateway
        self._pipeline = None

        if hf_gateway and hf_gateway.client:
            self._mode = "api"
            logger.info("DeepfakeDetector: HF Inference API mode (model={})", self.model_name)
        else:
            self._mode = "local"
            self._load_local_model(device)

    def _load_local_model(self, device):
        """Load the model locally (dev fallback). The pipeline handles preprocessing + softmax/sigmoid."""
        from transformers import pipeline

        logger.info("Loading deepfake detection model locally: {}", self.model_name)
        self._pipeline = pipeline("image-classification", model=self.model_name, top_k=None,
                                  device=device or "cpu")
        logger.info("Model loaded (labels: {})", self._pipeline.model.config.id2label)

    def predict_image(self, image_input: Union[str, Image.Image, np.ndarray]) -> Dict:
        """Predict if an image is a deepfake. Accepts path, PIL Image, or numpy array (BGR)."""
        if self._mode == "api":
            results = self._classify_api(image_input)
        else:
            results = self._pipeline(self._to_pil(image_input))
        return self._build_result(self._fake_probability(results))

    def _classify_api(self, image_input) -> list:
        """Send the image to the HF Inference API. Raises DetectorUnavailable if it fails."""
        tmp_path = None
        try:
            if isinstance(image_input, str):
                image_path = image_input
            else:
                # The API needs a file — save numpy/PIL input to a temp JPEG
                tmp = tempfile.NamedTemporaryFile(suffix=".jpg", delete=False)
                self._to_pil(image_input).save(tmp.name)
                tmp.close()
                tmp_path = image_path = tmp.name

            results = self._hf_gateway.classify_image(image_path, model=self.model_name)
        finally:
            if tmp_path and os.path.exists(tmp_path):
                os.unlink(tmp_path)

        # Fail closed: if the API is down we must NOT guess "REAL" — that would let fakes through
        if not results or results[0].get("label") == "error":
            raise DetectorUnavailable("Deepfake detection service unavailable")
        return results

    @staticmethod
    def _to_pil(image_input) -> Image.Image:
        if isinstance(image_input, str):
            return Image.open(image_input).convert("RGB")
        if isinstance(image_input, np.ndarray):  # OpenCV frames are BGR
            return Image.fromarray(cv2.cvtColor(image_input, cv2.COLOR_BGR2RGB))
        if isinstance(image_input, Image.Image):
            return image_input.convert("RGB")
        raise ValueError("Invalid image input type")

    @staticmethod
    def _fake_probability(results: list) -> float:
        """[{"label": "LABEL_0", "score": 0.93}, ...] -> 0.93 (sum of all 'fake' class scores)."""
        return min(1.0, sum(float(r["score"]) for r in results if r["label"].lower() in FAKE_LABELS))

    def _build_result(self, fake_prob: float) -> Dict:
        """Turn the fake probability into the standard result dict."""
        real_prob = 1.0 - fake_prob
        is_deepfake = fake_prob > config.DEEPFAKE_THRESHOLD
        confidence = fake_prob if is_deepfake else real_prob

        return {
            "is_deepfake": bool(is_deepfake),
            "confidence": float(round(confidence, 4)),
            "probabilities": {
                "real": float(round(real_prob, 4)),
                "fake": float(round(fake_prob, 4)),
            },
            "classification": "FAKE" if is_deepfake else "REAL",
            "risk_level": self._get_risk_level(fake_prob),
        }

    def predict_video(self, video_path: str, sample_frames: int = 30) -> Dict:
        """Analyze a video by sampling frames and running detection on each."""
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise ValueError(f"Could not open video: {video_path}")

        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        if total_frames <= 0:
            cap.release()
            raise ValueError("Video has no readable frames")
        frame_indices = np.linspace(0, total_frames - 1, min(sample_frames, total_frames), dtype=int)

        predictions = []
        for frame_idx in frame_indices:
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
            ret, frame = cap.read()
            if not ret:
                continue
            result = self.predict_image(frame)
            predictions.append(result)

        cap.release()
        if not predictions:
            raise ValueError("Could not decode any frames from video")

        fake_count = sum(1 for p in predictions if p["is_deepfake"])
        avg_fake_prob = np.mean([p["probabilities"]["fake"] for p in predictions])
        is_deepfake = fake_count > (len(predictions) * 0.5)

        return {
            "is_deepfake": bool(is_deepfake),
            "confidence": float(round(avg_fake_prob, 4)),
            "frames_analyzed": len(predictions),
            "fake_frames": int(fake_count),
            "fake_percentage": float(round(fake_count / len(predictions) * 100, 2)),
            "classification": "FAKE" if is_deepfake else "REAL",
            "risk_level": self._get_risk_level(avg_fake_prob),
            "frame_predictions": predictions[:5],
        }

    def _get_risk_level(self, fake_probability: float) -> str:
        if fake_probability >= 0.8:
            return "CRITICAL"
        elif fake_probability >= 0.6:
            return "HIGH"
        elif fake_probability >= 0.4:
            return "MEDIUM"
        else:
            return "LOW"
