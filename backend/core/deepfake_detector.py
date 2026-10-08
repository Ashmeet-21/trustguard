"""
Deepfake Detector Module — three ways to run the same model (config.DEEPFAKE_BACKEND):

  onnx   (default)  int8 ONNX file shipped in backend/models/, run with onnxruntime.
                    No PyTorch, no external API, no credits — fits Render's free 512MB plan,
                    and selfies never leave the server. Made by scripts/export_deepfake_onnx.py.
  api               HF Inference API (needs HF_TOKEN and paid credits).
  local             transformers + PyTorch (dev, and for benchmarking other models).

Model: buildborderless/CommunityForensics-DeepfakeDet-ViT.
Chosen by benchmarks/run_benchmark.py --compare: best of 8 models on fakes it had never seen
(AUC 0.88, 0% real photos wrongly flagged). See benchmarks/MODEL_COMPARISON.md.
"""

import tempfile
import os
from pathlib import Path

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

ONNX_PATH = Path(__file__).parent.parent / "models" / "deepfake_vit_int8.onnx"

# Pre-processing used by the model (from its CLIPImageProcessor config)
RESIZE_SHORTEST_EDGE = 440
CROP_SIZE = 384
CLIP_MEAN = np.array([0.48145466, 0.4578275, 0.40821073], dtype=np.float32)
CLIP_STD = np.array([0.26862954, 0.26130258, 0.27577711], dtype=np.float32)


def preprocess(image: Image.Image) -> np.ndarray:
    """PIL image -> (1, 3, 384, 384) float32 array, matching the model's own processor:
    resize shortest edge to 440 (bicubic), centre-crop 384, scale to 0..1, normalise."""
    w, h = image.size
    scale = RESIZE_SHORTEST_EDGE / min(w, h)
    image = image.resize((max(CROP_SIZE, int(w * scale)), max(CROP_SIZE, int(h * scale))), Image.BICUBIC)
    left = (image.width - CROP_SIZE) // 2
    top = (image.height - CROP_SIZE) // 2
    image = image.crop((left, top, left + CROP_SIZE, top + CROP_SIZE))
    pixels = (np.asarray(image, dtype=np.float32) / 255.0 - CLIP_MEAN) / CLIP_STD
    return pixels.transpose(2, 0, 1)[np.newaxis]  # HWC -> NCHW


class DeepfakeDetector:
    """Deepfake Detection using a pretrained Vision Transformer (ViT)."""

    def __init__(self, device: str = None, hf_gateway=None, model_name: str = None, backend: str = None):
        self.model_name = model_name or config.HF_IMAGE_MODEL
        self._hf_gateway = hf_gateway
        self._pipeline = None
        self._session = None

        # Comparing a different model (benchmark) always runs it locally with transformers
        backend = "local" if model_name else (backend or config.DEEPFAKE_BACKEND)

        if backend == "onnx" and ONNX_PATH.exists():
            self._mode = "onnx"
            self._load_onnx()
        elif backend == "api" and hf_gateway and hf_gateway.client:
            self._mode = "api"
            logger.info("DeepfakeDetector: HF Inference API mode (model={})", self.model_name)
        else:
            if backend != "local":
                logger.warning("DeepfakeDetector: '{}' backend unavailable, falling back to local transformers", backend)
            self._mode = "local"
            self._load_local_model(device)

    def _load_onnx(self):
        import onnxruntime as ort

        options = ort.SessionOptions()
        options.intra_op_num_threads = 2  # small server — keep memory and CPU use modest
        self._session = ort.InferenceSession(str(ONNX_PATH), options, providers=["CPUExecutionProvider"])
        logger.info("DeepfakeDetector: ONNX mode ({}, {:.1f} MB)", ONNX_PATH.name, ONNX_PATH.stat().st_size / 1e6)

    def _load_local_model(self, device):
        """Load the model locally (dev fallback). The pipeline handles preprocessing + softmax/sigmoid."""
        from transformers import pipeline

        logger.info("Loading deepfake detection model locally: {}", self.model_name)
        self._pipeline = pipeline("image-classification", model=self.model_name, top_k=None,
                                  device=device or "cpu")
        logger.info("Model loaded (labels: {})", self._pipeline.model.config.id2label)

    def predict_image(self, image_input: Union[str, Image.Image, np.ndarray]) -> Dict:
        """Predict if an image is a deepfake. Accepts path, PIL Image, or numpy array (BGR)."""
        if self._mode == "onnx":
            logit = self._session.run(None, {"pixel_values": preprocess(self._to_pil(image_input))})[0][0][0]
            results = [{"label": "LABEL_0", "score": float(1 / (1 + np.exp(-logit)))}]  # sigmoid -> p(fake)
        elif self._mode == "api":
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
            # 6 decimals: many real photos score ~0.0000x — rounding to 4 turns them into ties
            "probabilities": {
                "real": float(round(real_prob, 6)),
                "fake": float(round(fake_prob, 6)),
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
