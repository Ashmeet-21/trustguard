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

            # Check 4: Pitch Variation — human speech has changing pitch, synthetic is monotone
            pitch_score = self._check_pitch_variation(audio_data, sample_rate)

            # Weighted: spectral and pitch matter most for voice detection
            human_score = (
                0.30 * flatness_score
                + 0.20 * zcr_score
                + 0.20 * energy_score
                + 0.30 * pitch_score
            )
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

        Uses gradual scoring instead of hard buckets for better accuracy.
        """
        spectrum = np.abs(np.fft.rfft(audio))
        spectrum = spectrum[spectrum > 0]  # Remove zeros for log

        if len(spectrum) == 0:
            return 0.5

        geo_mean = np.exp(np.mean(np.log(spectrum + 1e-10)))
        arith_mean = np.mean(spectrum)

        flatness = geo_mean / (arith_mean + 1e-10)

        # Gradual curve: real speech flatness ~0.01-0.25, synthetic ~0.3-0.8
        # Browser-recorded 16kHz audio with ambient noise tends toward 0.1-0.3
        if flatness < 0.05:
            return 0.95
        elif flatness < 0.25:
            return 0.95 - (flatness - 0.05) / 0.20 * 0.25  # 0.95 → 0.70
        elif flatness < 0.40:
            return 0.70 - (flatness - 0.25) / 0.15 * 0.30  # 0.70 → 0.40
        elif flatness < 0.60:
            return 0.40 - (flatness - 0.40) / 0.20 * 0.15  # 0.40 → 0.25
        else:
            return max(0.1, 0.25 - (flatness - 0.60) * 0.5)

    def _check_zero_crossing_rate(self, audio: np.ndarray) -> float:
        """
        Zero-crossing rate = how often the signal switches from positive to negative.
        Human speech: moderate ZCR with high variance (vowels low, consonants high).
        Synthetic: more uniform ZCR.
        """
        chunk_size = 1024
        chunks = [audio[i:i + chunk_size] for i in range(0, len(audio) - chunk_size, chunk_size)]

        if len(chunks) < 2:
            return 0.5

        zcrs = []
        for chunk in chunks:
            crossings = np.sum(np.abs(np.diff(np.sign(chunk))) > 0)
            zcrs.append(crossings / len(chunk))

        zcr_variance = np.var(zcrs)

        # Gradual curve: human speech ZCR variance typically 0.002-0.05+
        # Browser microphone adds ambient noise which increases variance (good for human detection)
        if zcr_variance > 0.015:
            return 0.95
        elif zcr_variance > 0.005:
            return 0.70 + (zcr_variance - 0.005) / 0.010 * 0.25  # 0.70 → 0.95
        elif zcr_variance > 0.001:
            return 0.45 + (zcr_variance - 0.001) / 0.004 * 0.25  # 0.45 → 0.70
        else:
            return max(0.15, zcr_variance / 0.001 * 0.45)

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

        # Gradual curve: human speech CV typically 0.5-3.0+
        # Short browser recordings (3-10s) have slightly less variation
        if cv > 2.0:
            return 0.95
        elif cv > 1.0:
            return 0.75 + (cv - 1.0) / 1.0 * 0.20  # 0.75 → 0.95
        elif cv > 0.4:
            return 0.50 + (cv - 0.4) / 0.6 * 0.25   # 0.50 → 0.75
        elif cv > 0.1:
            return 0.25 + (cv - 0.1) / 0.3 * 0.25   # 0.25 → 0.50
        else:
            return max(0.1, cv / 0.1 * 0.25)

    def _check_pitch_variation(self, audio: np.ndarray, sample_rate: int) -> float:
        """
        Pitch variation — human speech naturally changes pitch (intonation).
        Synthetic/TTS audio tends to be more monotone or have unnatural pitch jumps.

        Uses autocorrelation to estimate fundamental frequency (F0) per chunk.
        Human F0: 85-300 Hz, with gradual variation across chunks.
        """
        chunk_size = int(sample_rate * 0.03)  # 30ms chunks
        hop = chunk_size // 2  # 50% overlap
        min_lag = int(sample_rate / 300)  # Max F0 = 300 Hz
        max_lag = int(sample_rate / 85)   # Min F0 = 85 Hz

        if max_lag >= chunk_size or len(audio) < chunk_size * 4:
            return 0.5  # Not enough data

        pitches = []
        for start in range(0, len(audio) - chunk_size, hop):
            chunk = audio[start:start + chunk_size]
            # Skip silent chunks
            if np.max(np.abs(chunk)) < 0.02:
                continue

            # Autocorrelation to find pitch
            corr = np.correlate(chunk, chunk, mode='full')
            corr = corr[len(corr) // 2:]  # Take positive lags only

            # Look for peak in the speech frequency range
            search_region = corr[min_lag:max_lag] if max_lag <= len(corr) else corr[min_lag:]
            if len(search_region) == 0:
                continue

            peak_idx = np.argmax(search_region) + min_lag
            if corr[peak_idx] > 0.3 * corr[0]:  # Confidence threshold
                f0 = sample_rate / peak_idx
                if 85 <= f0 <= 300:
                    pitches.append(f0)

        if len(pitches) < 3:
            return 0.5  # Not enough voiced frames

        pitch_std = np.std(pitches)
        pitch_mean = np.mean(pitches)

        # Human speech: pitch std typically 10-60 Hz (natural intonation)
        # Monotone synth: pitch std < 5 Hz
        # Glitchy synth: pitch std > 80 Hz (unnatural jumps)
        if 8 <= pitch_std <= 70:
            # Natural range — score based on how centered it is
            return min(0.95, 0.70 + (min(pitch_std, 40) - 8) / 32 * 0.25)
        elif pitch_std < 8:
            return max(0.2, pitch_std / 8 * 0.65)  # Too monotone
        else:
            return max(0.3, 0.95 - (pitch_std - 70) / 50 * 0.4)  # Too jumpy

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
