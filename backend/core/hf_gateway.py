"""
HuggingFace Inference Gateway — Thin wrapper around HuggingFace's Inference API.

All HF API calls go through this gateway so we have:
- Centralized token management
- Retry logic with backoff
- Logging of every call with latency
- Graceful fallback on errors

INTERVIEW TIP: "I created a gateway pattern so all external API calls go through
one place. This makes it easy to add retries, logging, and swap providers later."
"""

import time
from loguru import logger
from backend.utils import config


class DetectorUnavailable(RuntimeError):
    """Raised when a detection service can't give an answer (e.g. HF API down). main.py turns it into HTTP 503."""


class HFGateway:
    """Wrapper around HuggingFace InferenceClient for image and audio classification."""

    def __init__(self, token: str = None):
        self.token = token or config.HF_TOKEN
        self.client = None

        if self.token:
            try:
                from huggingface_hub import InferenceClient
                self.client = InferenceClient(token=self.token)
                logger.info("HF Gateway initialized with token")
            except ImportError:
                logger.warning("huggingface_hub not installed — HF Gateway disabled")
        else:
            logger.info("No HF_TOKEN set — HF Gateway disabled (will use local fallbacks)")

    def classify_audio(self, audio_path: str, model: str) -> list:
        """Audio classification, e.g. [{"label": "bonafide", "score": 0.95}, ...]. On failure: [{"label": "error", "score": 0}]"""
        return self._call_with_retries("audio_classification", audio_path, model)

    def classify_image(self, image_path: str, model: str) -> list:
        """Image classification, e.g. [{"label": "real", "score": 0.95}, ...]. On failure: [{"label": "error", "score": 0}]"""
        return self._call_with_retries("image_classification", image_path, model)

    def _call_with_retries(self, task: str, file_path: str, model: str, max_retries: int = 3) -> list:
        """Call an InferenceClient task (e.g. "image_classification") with 2s/4s backoff between retries."""
        if not self.client:
            return [{"label": "error", "score": 0}]

        for attempt in range(max_retries):
            try:
                start = time.time()
                result = getattr(self.client, task)(file_path, model=model)
                latency = round((time.time() - start) * 1000, 2)
                logger.info("HF {} | model={} | latency={}ms", task, model, latency)
                return [{"label": r.label, "score": float(r.score)} for r in result]
            except Exception as e:
                logger.warning("HF {} failed (attempt {}/{}): {}", task, attempt + 1, max_retries, e)
                # 4xx (bad token, bad request) won't fix itself — only retry server errors and 429 rate limits
                status = getattr(getattr(e, "response", None), "status_code", None)
                if status is not None and 400 <= status < 500 and status != 429:
                    break
                if attempt < max_retries - 1:
                    time.sleep((attempt + 1) * 2)

        logger.error("HF Gateway: all {} retries failed for model={}", max_retries, model)
        return [{"label": "error", "score": 0}]
