"""
Behavioral Biometrics Analyzer — Is this a REAL human or a BOT?

Pure rule-based statistical analysis. No ML needed.

Four checks on keystroke and mouse data:
1. Typing speed — bots type too fast (< 30ms between keys) or too uniform
2. Typing rhythm — humans have natural variance, bots are robotic
3. Mouse speed — bots teleport between points, humans move smoothly
4. Mouse straightness — humans have curved paths, bots go perfectly straight

Each check returns 0.0 (bot-like) to 1.0 (human-like).
Weighted average → final behavior score.

INTERVIEW TIP: "I used statistical anomaly detection instead of ML because
the rules are simple and explainable — if typing is too fast or too uniform,
it's probably a bot. No training data needed."
"""

import numpy as np
from loguru import logger

from backend.utils import config


class BehaviorAnalyzer:
    """Rule-based behavioral biometrics — detects bots from keystroke + mouse data."""

    WEIGHTS = {
        "typing_speed": 0.25,
        "typing_rhythm": 0.25,
        "mouse_speed": 0.25,
        "mouse_straightness": 0.25,
    }

    def __init__(self):
        self.threshold = config.BEHAVIOR_THRESHOLD
        logger.info("Behavior analyzer initialized (threshold={})", self.threshold)

    def analyze(self, data: dict) -> dict:
        """
        Analyze keystroke and mouse data for bot-like behavior.

        Args:
            data: dict with "keystrokes" and/or "mouse_movements" lists
                keystrokes: [{"key": "a", "timestamp_ms": 1234}, ...]
                mouse_movements: [{"x": 100, "y": 200, "timestamp_ms": 1234}, ...]

        Returns:
            dict with is_human, behavior_score, classification, risk_level, checks
        """
        keystrokes = data.get("keystrokes", [])
        mouse_movements = data.get("mouse_movements", [])

        # Calculate individual scores
        checks = {}
        available_weights = {}

        if len(keystrokes) >= 2:
            intervals = self._get_intervals(keystrokes)
            checks["typing_speed_score"] = self._check_typing_speed(intervals)
            checks["typing_rhythm_score"] = self._check_typing_rhythm(intervals)
            available_weights["typing_speed"] = self.WEIGHTS["typing_speed"]
            available_weights["typing_rhythm"] = self.WEIGHTS["typing_rhythm"]
        else:
            checks["typing_speed_score"] = 0.0
            checks["typing_rhythm_score"] = 0.0

        if len(mouse_movements) >= 2:
            checks["mouse_speed_score"] = self._check_mouse_speed(mouse_movements)
            checks["mouse_straightness_score"] = self._check_mouse_straightness(mouse_movements)
            available_weights["mouse_speed"] = self.WEIGHTS["mouse_speed"]
            available_weights["mouse_straightness"] = self.WEIGHTS["mouse_straightness"]
        else:
            checks["mouse_speed_score"] = 0.0
            checks["mouse_straightness_score"] = 0.0

        # Weighted average (only count checks that had data)
        if available_weights:
            total_weight = sum(available_weights.values())
            score_keys = {
                "typing_speed": "typing_speed_score",
                "typing_rhythm": "typing_rhythm_score",
                "mouse_speed": "mouse_speed_score",
                "mouse_straightness": "mouse_straightness_score",
            }
            behavior_score = sum(
                (available_weights[k] / total_weight) * checks[score_keys[k]]
                for k in available_weights
            )
        else:
            behavior_score = 0.0

        behavior_score = round(float(behavior_score), 4)
        is_human = behavior_score >= self.threshold

        return {
            "is_human": is_human,
            "behavior_score": behavior_score,
            "classification": "HUMAN" if is_human else "BOT",
            "risk_level": self._get_risk_level(behavior_score),
            "checks": checks,
        }

    def _get_intervals(self, keystrokes: list) -> list:
        """Extract time intervals between consecutive keystrokes."""
        timestamps = [k["timestamp_ms"] for k in keystrokes]
        return [timestamps[i + 1] - timestamps[i] for i in range(len(timestamps) - 1)]

    def _check_typing_speed(self, intervals: list) -> float:
        """
        Check average typing speed.
        Bots: < 30ms between keys (superhuman speed)
        Normal humans: 50-300ms between keys
        Very slow: > 500ms (might be confused, but still human)
        """
        if not intervals:
            return 0.0

        avg_interval = np.mean(intervals)

        if avg_interval < 20:
            return 0.1   # Way too fast — definitely a bot
        elif avg_interval < 40:
            return 0.3   # Suspiciously fast
        elif avg_interval < 50:
            return 0.6   # Fast but possible
        elif avg_interval <= 400:
            return 0.9   # Normal human range
        else:
            return 0.7   # Slow but still human

    def _check_typing_rhythm(self, intervals: list) -> float:
        """
        Check typing rhythm variance.
        Humans: natural variance in timing (some keys faster, some slower)
        Bots: very uniform timing (low standard deviation)
        """
        if len(intervals) < 3:
            return 0.5  # Not enough data

        std_dev = np.std(intervals)
        mean_interval = np.mean(intervals) + 1e-10
        cv = std_dev / mean_interval  # Coefficient of variation

        if cv < 0.05:
            return 0.1   # Almost zero variance — robotic
        elif cv < 0.15:
            return 0.4   # Low variance — suspicious
        elif cv < 0.60:
            return 0.9   # Natural human variance
        else:
            return 0.7   # High variance — still human (maybe distracted)

    def _check_mouse_speed(self, movements: list) -> float:
        """
        Check mouse movement speed.
        Bots: instant teleportation (0ms between points) or impossibly fast
        Humans: smooth movement with varying speed
        """
        if len(movements) < 2:
            return 0.0

        speeds = []
        for i in range(1, len(movements)):
            dx = movements[i]["x"] - movements[i - 1]["x"]
            dy = movements[i]["y"] - movements[i - 1]["y"]
            dt = movements[i]["timestamp_ms"] - movements[i - 1]["timestamp_ms"]

            if dt <= 0:
                speeds.append(float("inf"))
            else:
                distance = np.sqrt(dx ** 2 + dy ** 2)
                speeds.append(distance / dt)  # pixels per ms

        avg_speed = np.mean([s for s in speeds if s != float("inf")])
        speed_variance = np.var([s for s in speeds if s != float("inf")])

        # Too fast = bot. Natural mouse movement has varying speed.
        if avg_speed > 50:
            return 0.1   # Teleporting — bot
        elif avg_speed > 20:
            return 0.4   # Very fast
        elif speed_variance < 0.01:
            return 0.3   # Uniform speed — suspicious
        else:
            return 0.9   # Normal human movement

    def _check_mouse_straightness(self, movements: list) -> float:
        """
        Check if mouse paths are too straight.
        Humans: slightly curved, wobbly paths
        Bots: perfectly straight lines between points

        We measure path "efficiency" — actual distance vs straight-line distance.
        Ratio close to 1.0 = perfectly straight = bot-like.
        Ratio > 1.2 = curved/natural = human.

        Trackpad users and short movements naturally produce straighter paths,
        so we analyze multiple segments instead of just start-to-end.
        """
        if len(movements) < 3:
            return 0.5

        # Calculate actual path length
        actual_length = 0
        segment_lengths = []
        for i in range(1, len(movements)):
            dx = movements[i]["x"] - movements[i - 1]["x"]
            dy = movements[i]["y"] - movements[i - 1]["y"]
            seg = np.sqrt(dx ** 2 + dy ** 2)
            actual_length += seg
            segment_lengths.append(seg)

        # Straight-line distance (start to end)
        dx_total = movements[-1]["x"] - movements[0]["x"]
        dy_total = movements[-1]["y"] - movements[0]["y"]
        straight_length = np.sqrt(dx_total ** 2 + dy_total ** 2)

        if straight_length < 1:
            return 0.7  # Mouse barely moved — inconclusive

        # For short distances (< 200px), trackpad users move straighter — don't penalize
        if straight_length < 200:
            ratio = actual_length / straight_length
            if ratio < 1.01:
                return 0.4   # Still suspicious if PERFECTLY straight on short distance
            else:
                return 0.8   # Short distance with any wobble = fine

        # Path efficiency ratio
        ratio = actual_length / straight_length

        # Also check direction changes — humans change direction, bots don't
        direction_changes = 0
        for i in range(2, len(movements)):
            dx1 = movements[i - 1]["x"] - movements[i - 2]["x"]
            dy1 = movements[i - 1]["y"] - movements[i - 2]["y"]
            dx2 = movements[i]["x"] - movements[i - 1]["x"]
            dy2 = movements[i]["y"] - movements[i - 1]["y"]
            # Cross product sign change = direction change
            cross = dx1 * dy2 - dy1 * dx2
            if i > 2:
                prev_dx1 = movements[i - 2]["x"] - movements[i - 3]["x"]
                prev_dy1 = movements[i - 2]["y"] - movements[i - 3]["y"]
                prev_cross = prev_dx1 * dy1 - prev_dy1 * dx1
                if cross * prev_cross < 0:
                    direction_changes += 1

        dir_ratio = direction_changes / max(1, len(movements) - 2)

        # Combine path ratio and direction changes
        if ratio < 1.02 and dir_ratio < 0.05:
            return 0.2   # Almost perfectly straight with no direction changes — bot
        elif ratio < 1.05:
            return 0.4 + dir_ratio * 3  # Straight but some direction changes = less suspicious
        elif ratio < 2.0:
            return 0.85 + min(0.1, dir_ratio)  # Natural wobble — human
        else:
            return 0.7   # Very wobbly — still human (shaky hand)

    def _get_risk_level(self, behavior_score: float) -> str:
        """Higher behavior score = more human-like = lower risk."""
        if behavior_score >= 0.8:
            return "LOW"
        elif behavior_score >= 0.6:
            return "MEDIUM"
        elif behavior_score >= 0.4:
            return "HIGH"
        else:
            return "CRITICAL"
