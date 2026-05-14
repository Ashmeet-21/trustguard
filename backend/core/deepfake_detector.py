"""
Deepfake Detector Module

API mode (HF_TOKEN set):   calls HF Inference API — no torch needed, works on 512MB RAM
Local mode (no HF_TOKEN):  loads ViT model with torch (dev/local only)

Model: dima806/deepfake_vs_real_image_detection
"""

import tempfile
import os
import numpy as np
from PIL import Image
from loguru import logger
from typing import Dict, Union
import cv2


class DeepfakeDetector:
    """
    Deepfake Detection using a pretrained Vision Transformer (ViT).

    In production (HF_TOKEN set), inference goes through the HF Inference API.
    Locally, it loads the model with torch for offline use.
    """

    MODEL_NAME = "dima806/deepfake_vs_real_image_detection"

    def __init__(self, model_path: str = None, device: str = None, hf_gateway=None):
        self._hf_gateway = hf_gateway
        self._model = None
        self._processor = None
        self._device = None
        self._labels = None

        if hf_gateway and hf_gateway.client:
            self._mode = "api"
            logger.info("DeepfakeDetector: using HF Inference API mode")
        else:
            self._mode = "local"
            self._load_local_model(model_path, device)

    def _load_local_model(self, model_path, device):
        """Load ViT model locally using torch (dev fallback)."""
        import torch
        from transformers import ViTImageProcessor, ViTForImageClassification

        if device is None:
            if torch.cuda.is_available():
                self._device = torch.device("cuda")
            elif torch.backends.mps.is_available():
                self._device = torch.device("mps")
            else:
                self._device = torch.device("cpu")
        else:
            self._device = torch.device(device)

        logger.info("Using device: {}", self._device)
        logger.info("Loading deepfake detection model: {}", self.MODEL_NAME)
        self._processor = ViTImageProcessor.from_pretrained(self.MODEL_NAME)
        self._model = ViTForImageClassification.from_pretrained(self.MODEL_NAME)
        self._model.to(self._device)
        self._model.eval()
        self._labels = self._model.config.id2label
        logger.info("Model loaded successfully (labels: {})", self._labels)

    def predict_image(self, image_input: Union[str, Image.Image, np.ndarray]) -> Dict:
        """Predict if an image is a deepfake. Accepts path, PIL Image, or numpy array."""
        if self._mode == "api":
            return self._predict_api(image_input)
        return self._predict_local(image_input)

    def _predict_api(self, image_input: Union[str, Image.Image, np.ndarray]) -> Dict:
        """Call HF Inference API for classification."""
        tmp_path = None
        try:
            if isinstance(image_input, str):
                image_path = image_input
            else:
                # Convert numpy/PIL to temp file for API upload
                if isinstance(image_input, np.ndarray):
                    pil_image = Image.fromarray(cv2.cvtColor(image_input, cv2.COLOR_BGR2RGB))
                else:
                    pil_image = image_input.convert("RGB")
                tmp = tempfile.NamedTemporaryFile(suffix=".jpg", delete=False)
                pil_image.save(tmp.name)
                tmp.close()
                tmp_path = tmp.name
                image_path = tmp_path

            results = self._hf_gateway.classify_image(image_path, model=self.MODEL_NAME)
        finally:
            if tmp_path and os.path.exists(tmp_path):
                os.unlink(tmp_path)

        # Error fallback — default to uncertain REAL to avoid false positives
        if not results or results[0].get("label") == "error":
            logger.warning("HF API returned error, defaulting to REAL/uncertain")
            return {
                "is_deepfake": False,
                "confidence": 0.5,
                "probabilities": {"real": 0.5, "fake": 0.5},
                "classification": "REAL",
                "risk_level": "MEDIUM",
            }

        fake_prob = 0.0
        real_prob = 0.0
        for r in results:
            label = r["label"].lower()
            if label == "fake":
                fake_prob = float(r["score"])
            elif label == "real":
                real_prob = float(r["score"])

        # Normalize to sum to 1.0
        total = fake_prob + real_prob
        if total > 0:
            fake_prob /= total
            real_prob /= total

        is_deepfake = fake_prob > 0.5
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

    def _predict_local(self, image_input: Union[str, Image.Image, np.ndarray]) -> Dict:
        """Local torch inference (dev only)."""
        import torch

        if isinstance(image_input, str):
            image = Image.open(image_input).convert("RGB")
        elif isinstance(image_input, np.ndarray):
            image = Image.fromarray(cv2.cvtColor(image_input, cv2.COLOR_BGR2RGB))
        elif isinstance(image_input, Image.Image):
            image = image_input.convert("RGB")
        else:
            raise ValueError("Invalid image input type")

        inputs = self._processor(images=image, return_tensors="pt").to(self._device)

        with torch.no_grad():
            outputs = self._model(**inputs)
            probs = torch.nn.functional.softmax(outputs.logits, dim=1)[0]

        fake_idx = next(i for i, lbl in self._labels.items() if lbl.lower() == "fake")
        real_idx = next(i for i, lbl in self._labels.items() if lbl.lower() == "real")
        fake_prob = probs[fake_idx].item()
        real_prob = probs[real_idx].item()

        is_deepfake = fake_prob > 0.5
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
        frame_indices = np.linspace(0, total_frames - 1, sample_frames, dtype=int)

        predictions = []
        for frame_idx in frame_indices:
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
            ret, frame = cap.read()
            if not ret:
                continue
            result = self.predict_image(frame)
            predictions.append(result)

        cap.release()

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

    def batch_predict(self, image_paths: list) -> list:
        results = []
        for path in image_paths:
            try:
                result = self.predict_image(path)
                result["image_path"] = path
                results.append(result)
            except Exception as e:
                results.append({"image_path": path, "error": str(e), "is_deepfake": None})
        return results
