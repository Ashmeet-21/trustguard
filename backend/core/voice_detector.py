"""
Voice Deepfake Detector — Is this audio from a REAL human or AI-generated?

Two detection paths:
1. PRIMARY: HuggingFace API (when HF_TOKEN is set) — uses a pretrained model
2. FALLBACK: Local spectral analysis with scipy — simple but effective

The local fallback checks 3 things about the audio:
- Spectral flatness: Synthetic audio has a "flatter" frequency spectrum
- Zero-crossing rate: How often the audio signal crosses zero — different for human vs synthetic
- Energy variation: Human speech has dynamic range (loud/quiet), synthetic is more uniform

INTERVIEW TIP: "I built a two-tier system — cloud API for accuracy, local fallback for
reliability. The local checks use basic signal processing anyone can understand."
"""

import time
import numpy as np
from pathlib import Path
from loguru import logger

from backend.utils import config


class VoiceDetector:
    """Voice deepfake detection using HF API with local spectral fallback."""

    HF_MODEL = "MattyB95/AST-ASVspoof2019-Synthetic-Voice-Detection"

    def __init__(self, hf_gateway=None):
        self.hf_gateway = hf_gateway
        logger.info("Voice detector initialized (HF gateway={})", "enabled" if hf_gateway and hf_gateway.client else "disabled")

    def detect_voice(self, audio_path: str) -> dict:
        """
        Main method — detect if audio is synthetic.

        Tries HF API first, falls back to local analysis.

        Returns:
            dict with is_synthetic, confidence, human_score, synthetic_score,
            classification, risk_level, model_used, processing_time_ms
        """
        start = time.time()

        # Try HF API first
        if self.hf_gateway and self.hf_gateway.client:
            result = self._detect_via_hf(audio_path)
            if result is not None:
                result["processing_time_ms"] = round((time.time() - start) * 1000, 2)
                return result

        # Fall back to local analysis
        result = self._detect_local(audio_path)
        result["processing_time_ms"] = round((time.time() - start) * 1000, 2)
        return result

    def _detect_via_hf(self, audio_path: str) -> dict:
        """Call HF Inference API for audio classification."""
        try:
            predictions = self.hf_gateway.classify_audio(audio_path, self.HF_MODEL)

            if not predictions or predictions[0]["label"] == "error":
                return None

            # Parse HF response — model returns labels like "bonafide" and "spoof"
            human_score = 0.0
            synthetic_score = 0.0

            for pred in predictions:
                label = pred["label"].lower()
                if label in ("bonafide", "real", "human", "genuine"):
                    human_score = pred["score"]
                elif label in ("spoof", "fake", "synthetic", "cloned"):
                    synthetic_score = pred["score"]

            # If we didn't find expected labels, use first two
            if human_score == 0.0 and synthetic_score == 0.0 and len(predictions) >= 2:
                human_score = predictions[0]["score"]
                synthetic_score = predictions[1]["score"]

            is_synthetic = synthetic_score > human_score
            confidence = max(human_score, synthetic_score)

            return {
                "is_synthetic": bool(is_synthetic),
                "confidence": round(float(confidence), 4),
                "human_score": round(float(human_score), 4),
                "synthetic_score": round(float(synthetic_score), 4),
                "classification": "SYNTHETIC" if is_synthetic else "HUMAN",
                "risk_level": self._get_risk_level(synthetic_score),
                "model_used": "hf_api",
            }

        except Exception as e:
            logger.warning("HF voice detection failed: {} — falling back to local", e)
            return None

    def _detect_local(self, audio_path: str) -> dict:
        """
        Local fallback — spectral analysis using scipy.

        Three checks:
        1. Spectral flatness — synthetic audio is "flatter" (more uniform frequencies)
        2. Zero-crossing rate — how often signal crosses zero
        3. Energy variation — human speech has more dynamic range
        """
        try:
            import scipy.io.wavfile as wavfile

            sample_rate, audio_data = wavfile.read(audio_path)

            # Convert stereo to mono if needed
            if len(audio_data.shape) > 1:
                audio_data = audio_data.mean(axis=1)

            # Normalize to float -1.0 to 1.0
            audio_data = audio_data.astype(np.float64)
            max_val = np.max(np.abs(audio_data))
            if max_val > 0:
                audio_data = audio_data / max_val

            # Check 1: Spectral Flatness
            flatness_score = self._check_spectral_flatness(audio_data)

            # Check 2: Zero-Crossing Rate
            zcr_score = self._check_zero_crossing_rate(audio_data)

            # Check 3: Energy Variation
            energy_score = self._check_energy_variation(audio_data)

            # Weighted average — all three contribute equally
            human_score = (flatness_score + zcr_score + energy_score) / 3.0
            synthetic_score = 1.0 - human_score

            is_synthetic = synthetic_score > 0.5

            return {
                "is_synthetic": bool(is_synthetic),
                "confidence": round(float(max(human_score, synthetic_score)), 4),
                "human_score": round(float(human_score), 4),
                "synthetic_score": round(float(synthetic_score), 4),
                "classification": "SYNTHETIC" if is_synthetic else "HUMAN",
                "risk_level": self._get_risk_level(synthetic_score),
                "model_used": "local_spectral",
            }

        except Exception as e:
            logger.error("Local voice detection failed: {}", e)
            return {
                "is_synthetic": False,
                "confidence": 0.0,
                "human_score": 0.0,
                "synthetic_score": 0.0,
                "classification": "UNKNOWN",
                "risk_level": "MEDIUM",
                "model_used": "error",
            }

    def _check_spectral_flatness(self, audio: np.ndarray) -> float:
        """
        Spectral flatness = geometric mean / arithmetic mean of power spectrum.
        Real speech: lower flatness (has clear peaks at vocal frequencies).
        Synthetic: higher flatness (more uniform spectrum).
        Score closer to 1.0 = more human-like.
        """
        spectrum = np.abs(np.fft.rfft(audio))
        spectrum = spectrum[spectrum > 0]  # Remove zeros for log

        if len(spectrum) == 0:
            return 0.5

        geo_mean = np.exp(np.mean(np.log(spectrum + 1e-10)))
        arith_mean = np.mean(spectrum)

        flatness = geo_mean / (arith_mean + 1e-10)

        # Real speech: flatness ~0.01-0.3. Synthetic: ~0.3-0.8
        # Lower flatness = more human-like
        if flatness < 0.15:
            return 0.9  # Very human-like
        elif flatness < 0.35:
            return 0.7  # Probably human
        elif flatness < 0.55:
            return 0.4  # Uncertain
        else:
            return 0.2  # Likely synthetic

    def _check_zero_crossing_rate(self, audio: np.ndarray) -> float:
        """
        Zero-crossing rate = how often the signal switches from positive to negative.
        Human speech: moderate ZCR with high variance (vowels low, consonants high).
        Synthetic: more uniform ZCR.
        """
        # Split into small chunks and measure ZCR variance
        chunk_size = 1024
        chunks = [audio[i:i + chunk_size] for i in range(0, len(audio) - chunk_size, chunk_size)]

        if len(chunks) < 2:
            return 0.5

        zcrs = []
        for chunk in chunks:
            crossings = np.sum(np.abs(np.diff(np.sign(chunk))) > 0)
            zcrs.append(crossings / len(chunk))

        zcr_variance = np.var(zcrs)

        # Human speech has high variance in ZCR (quiet parts vs loud parts)
        if zcr_variance > 0.01:
            return 0.9  # High variance = natural
        elif zcr_variance > 0.005:
            return 0.7
        elif zcr_variance > 0.001:
            return 0.4
        else:
            return 0.2  # Too uniform = synthetic

    def _check_energy_variation(self, audio: np.ndarray) -> float:
        """
        Energy variation — human speech has loud and quiet parts (dynamic range).
        Synthetic audio often has more uniform energy levels.
        """
        chunk_size = 1024
        chunks = [audio[i:i + chunk_size] for i in range(0, len(audio) - chunk_size, chunk_size)]

        if len(chunks) < 2:
            return 0.5

        energies = [np.sum(chunk ** 2) / len(chunk) for chunk in chunks]
        energy_std = np.std(energies)
        energy_mean = np.mean(energies) + 1e-10

        # Coefficient of variation — how much energy varies relative to its mean
        cv = energy_std / energy_mean

        if cv > 1.5:
            return 0.9  # High variation = natural speech
        elif cv > 0.8:
            return 0.7
        elif cv > 0.3:
            return 0.4
        else:
            return 0.2  # Too uniform = synthetic

    def _get_risk_level(self, synthetic_score: float) -> str:
        """Map synthetic score to risk level (same pattern as deepfake/liveness)."""
        if synthetic_score >= 0.8:
            return "CRITICAL"
        elif synthetic_score >= 0.6:
            return "HIGH"
        elif synthetic_score >= 0.4:
            return "MEDIUM"
        else:
            return "LOW"
