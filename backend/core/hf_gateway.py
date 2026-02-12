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
        """
        Send audio to HF Inference API for classification.

        Args:
            audio_path: Path to audio file (WAV/MP3)
            model: HF model ID (e.g., "MattyB95/AST-ASVspoof2019-Synthetic-Voice-Detection")

        Returns:
            List of dicts: [{"label": "bonafide", "score": 0.95}, ...]
            On failure: [{"label": "error", "score": 0}]
        """
        if not self.client:
            return [{"label": "error", "score": 0}]

        max_retries = 3
        for attempt in range(max_retries):
            try:
                start = time.time()
                result = self.client.audio_classification(audio_path, model=model)
                latency = round((time.time() - start) * 1000, 2)
                logger.info("HF audio_classification | model={} | latency={}ms", model, latency)

                # Convert to simple dicts
                return [{"label": r.label, "score": float(r.score)} for r in result]

            except Exception as e:
                wait = (attempt + 1) * 2  # 2s, 4s, 6s backoff
                logger.warning("HF call failed (attempt {}/{}): {} — retrying in {}s", attempt + 1, max_retries, e, wait)
                if attempt < max_retries - 1:
                    time.sleep(wait)

        logger.error("HF Gateway: all {} retries failed for model={}", max_retries, model)
        return [{"label": "error", "score": 0}]

    def classify_image(self, image_path: str, model: str) -> list:
        """
        Send image to HF Inference API for classification.

        Returns:
            List of dicts: [{"label": "real", "score": 0.95}, ...]
            On failure: [{"label": "error", "score": 0}]
        """
        if not self.client:
            return [{"label": "error", "score": 0}]

        max_retries = 3
        for attempt in range(max_retries):
            try:
                start = time.time()
                result = self.client.image_classification(image_path, model=model)
                latency = round((time.time() - start) * 1000, 2)
                logger.info("HF image_classification | model={} | latency={}ms", model, latency)

                return [{"label": r.label, "score": float(r.score)} for r in result]

            except Exception as e:
                wait = (attempt + 1) * 2
                logger.warning("HF call failed (attempt {}/{}): {} — retrying in {}s", attempt + 1, max_retries, e, wait)
                if attempt < max_retries - 1:
                    time.sleep(wait)

        logger.error("HF Gateway: all {} retries failed for model={}", max_retries, model)
        return [{"label": "error", "score": 0}]
