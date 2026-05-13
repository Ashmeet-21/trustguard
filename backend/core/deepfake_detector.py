"""
Deepfake Detector Module
Uses a pretrained ViT (Vision Transformer) model from HuggingFace
for real vs fake face classification with 99%+ accuracy.

Model: dima806/deepfake_vs_real_image_detection
"""

import torch
import numpy as np
from PIL import Image
from loguru import logger
from typing import Dict, Union
from transformers import ViTImageProcessor, ViTForImageClassification
import cv2


class DeepfakeDetector:
    """
    Deepfake Detection using a pretrained Vision Transformer (ViT).

    How it works:
    1. Load pretrained ViT model from HuggingFace (downloads once, cached after)
    2. Preprocess image using the model's own processor
    3. Run inference → get probabilities for [fake, real]
    4. Return result with confidence and risk level
    """

    # HuggingFace model ID — pretrained on deepfake datasets, 99.27% accuracy
    MODEL_NAME = "dima806/deepfake_vs_real_image_detection"

    def __init__(self, model_path: str = None, device: str = None):
        # Pick best available device
        if device is None:
            if torch.cuda.is_available():
                self.device = torch.device("cuda")
            elif torch.backends.mps.is_available():
                self.device = torch.device("mps")
            else:
                self.device = torch.device("cpu")
        else:
            self.device = torch.device(device)

        logger.info("Using device: {}", self.device)

        # Load pretrained model and processor from HuggingFace
        logger.info("Loading deepfake detection model: {}", self.MODEL_NAME)
        self.processor = ViTImageProcessor.from_pretrained(self.MODEL_NAME)
        self.model = ViTForImageClassification.from_pretrained(self.MODEL_NAME)
        self.model.to(self.device)
        self.model.eval()

        # Model labels (read from model config so it's always correct)
        self.labels = self.model.config.id2label
        logger.info("Model loaded successfully (labels: {})", self.labels)

    def predict_image(self, image_input: Union[str, Image.Image, np.ndarray]) -> Dict:
        """
        Predict if an image is a deepfake.

        Args:
            image_input: File path, PIL Image, or numpy array

        Returns:
            Dict with is_deepfake, confidence, classification, risk_level, probabilities
        """
        # Convert input to PIL Image
        if isinstance(image_input, str):
            image = Image.open(image_input).convert("RGB")
        elif isinstance(image_input, np.ndarray):
            image = Image.fromarray(cv2.cvtColor(image_input, cv2.COLOR_BGR2RGB))
        elif isinstance(image_input, Image.Image):
            image = image_input.convert("RGB")
        else:
            raise ValueError("Invalid image input type")

        # Preprocess with the model's own processor (handles resize + normalize)
        inputs = self.processor(images=image, return_tensors="pt").to(self.device)

        # Run inference
        with torch.no_grad():
            outputs = self.model(**inputs)
            probs = torch.nn.functional.softmax(outputs.logits, dim=1)[0]

        # Use model's own label mapping to get correct indices
        # Model id2label: {0: 'Real', 1: 'Fake'}
        fake_idx = next(i for i, lbl in self.labels.items() if lbl.lower() == "fake")
        real_idx = next(i for i, lbl in self.labels.items() if lbl.lower() == "real")
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
        """
        Analyze a video by sampling frames and running detection on each.

        Uses majority voting — if >50% of frames are fake, the video is fake.
        """
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

        # Aggregate — majority vote
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
            "frame_predictions": predictions[:5],  # First 5 as sample
        }

    def _get_risk_level(self, fake_probability: float) -> str:
        """Map fake probability to a human-readable risk level."""
        if fake_probability >= 0.8:
            return "CRITICAL"
        elif fake_probability >= 0.6:
            return "HIGH"
        elif fake_probability >= 0.4:
            return "MEDIUM"
        else:
            return "LOW"

    def batch_predict(self, image_paths: list) -> list:
        """Run prediction on multiple images."""
        results = []
        for path in image_paths:
            try:
                result = self.predict_image(path)
                result["image_path"] = path
                results.append(result)
            except Exception as e:
                results.append({"image_path": path, "error": str(e), "is_deepfake": None})
        return results
