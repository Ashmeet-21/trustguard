"""
Liveness Detector — Is this a REAL person or a FAKE (photo/screen/mask)?

Think of it like a bouncer at a club checking if your ID photo is real:
- Does a face exist?               (Face Detection)
- Does the skin look like real skin or a printed paper?  (Texture Check)
- Are there weird screen patterns like when you photograph a TV?  (Frequency Check)
- Do the colors look natural or washed out like a printout?  (Color Check)
- Are the edges normal or too smooth/sharp like a screenshot?  (Edge Check)
- Is the image in focus like a real camera, not blurry like a photo-of-a-photo?  (Sharpness Check)

Each check gives a score 0.0 (fake) to 1.0 (real).
We average them all → final liveness score. Above 0.7 = LIVE, below = SPOOF.
"""

import cv2
import numpy as np
from PIL import Image
from typing import Dict, Union
from loguru import logger

import mediapipe as mp

from backend.utils import config


class LivenessDetector:

    # How much each check matters (adds up to 1.0)
    # Texture and sharpness matter most because they're the best at catching fakes
    WEIGHTS = {
        "texture": 0.25,
        "frequency": 0.20,
        "color": 0.20,
        "edge": 0.15,
        "sharpness": 0.20,
    }

    def __init__(self):
        # MediaPipe Face Mesh — Google's free face detector
        # It finds 468 points on a face (eyes, nose, mouth, jawline, etc.)
        self.face_mesh = mp.solutions.face_mesh.FaceMesh(
            static_image_mode=True,     # We're analyzing photos, not video stream
            max_num_faces=1,            # We only need one face
            min_detection_confidence=0.5,
        )
        self.threshold = config.LIVENESS_THRESHOLD  # Default 0.7
        logger.info("Liveness detector initialized (threshold={})", self.threshold)

    def detect_liveness(self, image_input: Union[str, Image.Image, np.ndarray]) -> Dict:
        """
        Main method — run all 6 checks on an image.

        Accepts: file path, PIL Image, or numpy array (BGR format from OpenCV)
        Returns: dict with is_live, score, individual check results
        """
        # Step 0: Convert whatever input we got into OpenCV format (BGR numpy array)
        bgr = self._load_image(image_input)

        # Step 1: Find the face — if no face, everything else is less reliable
        face_detected, face_region = self._detect_face(bgr)

        # Analyze just the face area (more accurate), or full image if no face found
        region = face_region if face_region is not None else bgr

        # Step 2-6: Run each check — each returns 0.0 (likely fake) to 1.0 (likely real)
        texture_score = self._check_texture(region)
        frequency_score = self._check_frequency(region)
        color_score = self._check_color(region)
        edge_score = self._check_edges(region)
        sharpness_score = self._check_sharpness(region)

        # Combine all scores using weights (like a grade: 25% texture + 20% frequency + ...)
        liveness_score = (
            self.WEIGHTS["texture"] * texture_score
            + self.WEIGHTS["frequency"] * frequency_score
            + self.WEIGHTS["color"] * color_score
            + self.WEIGHTS["edge"] * edge_score
            + self.WEIGHTS["sharpness"] * sharpness_score
        )

        # No face found? Cut the score in half — can't trust other checks without a face
        if not face_detected:
            liveness_score *= 0.5

        liveness_score = round(float(liveness_score), 4)
        is_live = liveness_score >= self.threshold

        return {
            "is_live": is_live,
            "liveness_score": liveness_score,
            "checks": {
                "face_detected": face_detected,
                "texture_score": round(float(texture_score), 4),
                "frequency_score": round(float(frequency_score), 4),
                "color_score": round(float(color_score), 4),
                "edge_score": round(float(edge_score), 4),
                "sharpness_score": round(float(sharpness_score), 4),
            },
            "risk_level": self._get_risk_level(liveness_score),
            "classification": "LIVE" if is_live else "SPOOF",
        }

    # ── Helper: Load Image ──────────────────────────────────

    def _load_image(self, image_input: Union[str, Image.Image, np.ndarray]) -> np.ndarray:
        """Convert file path / PIL Image / numpy array → BGR numpy array for OpenCV."""
        if isinstance(image_input, str):
            bgr = cv2.imread(image_input)
            if bgr is None:
                raise ValueError(f"Could not read image: {image_input}")
            return bgr
        elif isinstance(image_input, Image.Image):
            rgb_array = np.array(image_input.convert("RGB"))
            return cv2.cvtColor(rgb_array, cv2.COLOR_RGB2BGR)
        elif isinstance(image_input, np.ndarray):
            return image_input.copy()
        else:
            raise ValueError(f"Invalid image input type: {type(image_input)}")

    # ── Check 1: Face Detection ─────────────────────────────

    def _detect_face(self, bgr: np.ndarray):
        """
        WHY: If there's no face, it's probably not a person at all.
             Also, we want to crop just the face area for the other checks.

        HOW: MediaPipe finds 468 face landmarks (dots on eyes, nose, mouth).
             We use those dots to draw a box around the face and crop it.
        """
        rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
        results = self.face_mesh.process(rgb)

        if not results.multi_face_landmarks:
            return False, None

        # Get face bounding box from the landmark points
        h, w = bgr.shape[:2]
        landmarks = results.multi_face_landmarks[0]
        xs = [lm.x for lm in landmarks.landmark]
        ys = [lm.y for lm in landmarks.landmark]

        # Landmarks are 0-1 percentages, so multiply by image size to get pixels
        # Add 20px padding around the face so we don't crop too tight
        x_min = max(0, int(min(xs) * w) - 20)
        y_min = max(0, int(min(ys) * h) - 20)
        x_max = min(w, int(max(xs) * w) + 20)
        y_max = min(h, int(max(ys) * h) + 20)

        face_region = bgr[y_min:y_max, x_min:x_max]
        if face_region.size == 0:
            return True, None

        return True, face_region

    # ── Check 2: Texture (LBP) ──────────────────────────────

    def _check_texture(self, bgr: np.ndarray) -> float:
        """
        WHY: Real skin has tiny bumps, pores, and wrinkles = lots of texture variety.
             A printed photo or screen is FLAT — the texture is uniform/repetitive.

        HOW: LBP (Local Binary Pattern) — for each pixel, compare it to its 8 neighbors.
             If neighbor is brighter → 1, darker → 0. That gives an 8-bit pattern.
             Real faces have MANY different patterns. Fakes have fewer (less variety).
             We measure this variety using histogram variance.
        """
        gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)

        # Compare each pixel with its 8 neighbors (up, down, left, right, diagonals)
        # Build an 8-bit code: neighbor brighter than center = 1, else = 0
        lbp = np.zeros_like(gray, dtype=np.uint8)
        for dy, dx in [(-1, -1), (-1, 0), (-1, 1), (0, 1), (1, 1), (1, 0), (1, -1), (0, -1)]:
            neighbor = np.roll(np.roll(gray, dy, axis=0), dx, axis=1)
            lbp = (lbp << 1) | (neighbor >= gray).astype(np.uint8)

        # Count how many times each pattern appears (histogram)
        hist = cv2.calcHist([lbp], [0], None, [256], [0, 256]).flatten()
        hist = hist / hist.sum()  # Normalize to percentages

        # High variance = many different patterns = real skin texture
        variance = np.var(hist)
        score = min(1.0, variance / 0.0005)  # Normalize to 0-1 range
        return score

    # ── Check 3: Frequency (FFT) ────────────────────────────

    def _check_frequency(self, bgr: np.ndarray) -> float:
        """
        WHY: When you take a photo of a screen, you get "moire patterns" —
             those weird rainbow/grid lines you see when photographing a monitor.
             These show up as unusual spikes in high-frequency areas.

        HOW: FFT (Fast Fourier Transform) breaks an image into frequency components.
             Think of it like music: bass = low frequency (smooth areas),
             treble = high frequency (edges/details).
             A natural photo has a smooth falloff from bass to treble.
             A screen photo has weird treble spikes = moire patterns.
        """
        gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
        gray = cv2.resize(gray, (256, 256))  # Standard size for consistent analysis

        # Break image into frequency components
        f_transform = np.fft.fft2(gray.astype(np.float32))
        f_shift = np.fft.fftshift(f_transform)  # Move low-freq to center
        magnitude = np.log1p(np.abs(f_shift))    # Log scale so we can see the differences

        # Split into "inner circle" (low freq) and "outer ring" (high freq)
        h, w = magnitude.shape
        center_y, center_x = h // 2, w // 2
        radius = min(h, w) // 4

        # Mask: True for pixels far from center (high frequency)
        y, x = np.ogrid[:h, :w]
        is_high_freq = ((y - center_y) ** 2 + (x - center_x) ** 2) > radius ** 2

        high_freq_energy = magnitude[is_high_freq].mean()
        total_energy = magnitude.mean()

        # Ratio close to 1.0 = natural balance. Far from 1.0 = suspicious
        ratio = high_freq_energy / (total_energy + 1e-10)
        score = 1.0 - min(1.0, abs(ratio - 1.0) * 2)
        return max(0.0, score)

    # ── Check 4: Color Distribution ─────────────────────────

    def _check_color(self, bgr: np.ndarray) -> float:
        """
        WHY: Real cameras capture rich, spread-out colors.
             Printed photos lose color range (ink can't match a screen).
             Screen photos have artificial color banding (limited color steps).
             Both result in "clumpy" color histograms instead of smooth ones.

        HOW: Convert to YCrCb (brightness + color channels, better for skin).
             For each channel, measure "entropy" — how spread out the colors are.
             High entropy = many different colors = natural.
             Low entropy = few colors clustered together = likely a copy.
        """
        ycrcb = cv2.cvtColor(bgr, cv2.COLOR_BGR2YCrCb)

        scores = []
        for channel in range(3):  # Y (brightness), Cr (red tint), Cb (blue tint)
            hist = cv2.calcHist([ycrcb], [channel], None, [256], [0, 256]).flatten()
            hist = hist / hist.sum()  # Normalize to probabilities

            # Entropy formula: -sum(p * log2(p)) — higher = more spread out
            nonzero = hist[hist > 0]
            entropy = -np.sum(nonzero * np.log2(nonzero))

            # Max possible entropy for 256 bins = 8.0. Real faces are usually 5.5-7.5
            scores.append(min(1.0, entropy / 7.0))

        return float(np.mean(scores))  # Average of all 3 channels

    # ── Check 5: Edge Density ───────────────────────────────

    def _check_edges(self, bgr: np.ndarray) -> float:
        """
        WHY: Real faces have a natural amount of edges (eyebrows, lips, nose shadow).
             Printed photos are smoother — edges get softened by printing.
             Screen replays can be overly sharp — pixel-perfect edges.
             So we want "medium" edge density — not too smooth, not too sharp.

        HOW: Canny edge detection finds edges (boundaries between light/dark areas).
             We count what percentage of pixels are edges.
             ~5-15% is normal for a face. Too low = print. Too high = screen.
        """
        gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 50, 150)  # Find edges (white = edge, black = not)

        # What fraction of pixels are edges?
        density = edges.sum() / (255.0 * edges.size)

        # Sweet spot is around 3-20% edge density
        if 0.03 <= density <= 0.20:
            # Closer to 10% = better score
            score = 1.0 - abs(density - 0.10) / 0.10
        else:
            # Way outside normal range = likely fake
            score = max(0.0, 0.5 - abs(density - 0.10) * 3)

        return max(0.0, min(1.0, score))

    # ── Check 6: Sharpness (Laplacian) ──────────────────────

    def _check_sharpness(self, bgr: np.ndarray) -> float:
        """
        WHY: A photo-of-a-photo is always blurrier than the original (double capture).
             A screen replay might be overly sharp (pixel-perfect digital copy).
             Real camera photos have natural sharpness — somewhere in between.

        HOW: Laplacian measures how much neighboring pixels differ from each other.
             High variance = sharp image, low variance = blurry image.
             We want moderate sharpness (variance 50-3000).
             Too low (< 50) = blurry print/photo-of-photo.
             Too high (> 3000) = artificially sharp screen.
        """
        gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
        sharpness = cv2.Laplacian(gray, cv2.CV_64F).var()

        # Score based on where sharpness falls
        if sharpness < 10:
            score = 0.2        # Very blurry = likely a bad copy
        elif sharpness < 50:
            score = 0.5        # Somewhat blurry = suspicious
        elif sharpness < 3000:
            score = min(1.0, 0.6 + (sharpness / 3000) * 0.4)  # Normal range = good
        else:
            score = max(0.3, 1.0 - (sharpness - 3000) / 10000)  # Too sharp = suspicious

        return max(0.0, min(1.0, score))

    # ── Risk Level Mapping ──────────────────────────────────

    def _get_risk_level(self, liveness_score: float) -> str:
        """
        Higher liveness score = more likely real = lower risk.
        0.8+ = LOW risk (probably real)
        0.6+ = MEDIUM risk (uncertain)
        0.4+ = HIGH risk (probably fake)
        below 0.4 = CRITICAL (almost certainly fake)
        """
        if liveness_score >= 0.8:
            return "LOW"
        elif liveness_score >= 0.6:
            return "MEDIUM"
        elif liveness_score >= 0.4:
            return "HIGH"
        else:
            return "CRITICAL"
