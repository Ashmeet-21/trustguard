"""
Session Orchestrator — Manages end-to-end verification sessions.

A "session" is one verification attempt. The user submits an image,
optionally audio and behavior data, and the orchestrator:
1. Creates a session with a unique ID
2. Runs whichever agents have data (image -> deepfake + liveness, audio -> voice, JSON -> behavior)
3. Feeds all results into the Risk Engine
4. Returns a final trust_score + decision + per-agent breakdown

INTERVIEW TIP: "The orchestrator is like a project manager. It creates a session,
delegates work to each detection agent, collects their reports, and then asks
the risk engine to make the final call."
"""

import random
import time
import uuid
import threading
from datetime import datetime, timedelta
from collections import OrderedDict
from loguru import logger


# Session limits
MAX_SESSIONS = 10000
SESSION_TTL_HOURS = 24

# Head-turn challenge (R1). Yaw = nose position between the face edges, minus 0.5 (see LivenessDetector.head_yaw).
# The camera preview + snapshot are mirrored, so turning towards your LEFT shoulder moves the nose to image-left (negative).
# NOTE: these numbers are first guesses, to be checked on real webcam frames.
CHALLENGE_TTL_MINUTES = 10   # long enough for photo + voice + typing steps
FRONT_MAX_YAW = 0.15         # front photo must be roughly straight (real webcam fronts ranged -0.08 .. +0.14)
TURN_MIN_YAW = 0.10          # turned photo must be this much further than the front photo, in the asked direction


def head_turn_passes(asked: str, front_yaw: float, turn_yaw: float):
    """The head-turn rule in one place (also used by benchmarks/headturn_test.py). Returns (passed, reason)."""
    if abs(front_yaw) > FRONT_MAX_YAW:
        return False, "front photo not straight"
    change = turn_yaw - front_yaw  # compared with the user's own front photo; left = negative
    if (change <= -TURN_MIN_YAW) if asked == "left" else (change >= TURN_MIN_YAW):
        return True, ""
    return False, f"head not turned {asked}"


class SessionOrchestrator:
    """Coordinates multiple detection agents and produces a unified verification result."""

    def __init__(self, deepfake_detector, liveness_detector, voice_detector, behavior_analyzer, risk_engine):
        self.deepfake_detector = deepfake_detector
        self.liveness_detector = liveness_detector
        self.voice_detector = voice_detector
        self.behavior_analyzer = behavior_analyzer
        self.risk_engine = risk_engine
        self.sessions = OrderedDict()  # Ordered for efficient eviction
        self._lock = threading.Lock()
        logger.info("Session orchestrator initialized")

    def _cleanup_expired(self):
        """Remove sessions older than TTL."""
        cutoff = datetime.utcnow() - timedelta(hours=SESSION_TTL_HOURS)
        expired = []
        for sid, session in self.sessions.items():
            try:
                created = datetime.fromisoformat(session["created_at"])
                if created < cutoff:
                    expired.append(sid)
                else:
                    break  # OrderedDict: older entries first, so stop early
            except (ValueError, KeyError):
                expired.append(sid)
        for sid in expired:
            del self.sessions[sid]
        if expired:
            logger.info("Cleaned up {} expired sessions", len(expired))

    def create_session(self, user_id: int = None) -> str:
        """Create a new verification session, returns session_id. user_id = owner (None = anonymous)."""
        with self._lock:
            self._cleanup_expired()

            # Enforce max sessions cap
            if len(self.sessions) >= MAX_SESSIONS:
                # Evict oldest session
                self.sessions.popitem(last=False)

            session_id = str(uuid.uuid4())
            self.sessions[session_id] = {
                "session_id": session_id,
                "created_at": datetime.utcnow().isoformat(),
                "user_id": user_id,
                "status": "created",
                "challenge": random.SystemRandom().choice(["left", "right"]),  # server picks, client cannot
                "challenge_expires_at": (datetime.utcnow() + timedelta(minutes=CHALLENGE_TTL_MINUTES)).isoformat(),
                "agents": {},
                "result": None,
            }
            logger.info("Session created: {} asked={}", session_id, self.sessions[session_id]["challenge"])
            return session_id

    def run_session(self, session_id: str, image_path=None, audio_path=None, behavior_data=None, turn_image_path=None) -> dict:
        """
        Run verification agents based on provided inputs.

        Args:
            session_id: ID from create_session()
            image_path: Path to image file (runs deepfake + liveness)
            audio_path: Path to audio file (runs voice detection)
            behavior_data: dict with keystrokes + mouse_movements
            turn_image_path: second photo, head turned in the direction the session asked for

        Returns:
            Full session result with trust_score, decision, per-agent details
        """
        with self._lock:
            if session_id not in self.sessions:
                return {"error": "Session not found"}
            session = self.sessions[session_id]
            # One attempt per session — otherwise an attacker could keep retrying until PASS
            if session["status"] != "created":
                return {"error": f"Session already {session['status']}"}
            session["status"] = "processing"

        start = time.time()
        signals = {}

        # Run image agents (deepfake + liveness)
        if image_path and self.deepfake_detector:
            try:
                df_result = self.deepfake_detector.predict_image(image_path)
                df_score = round((1 - df_result["probabilities"]["fake"]) * 100, 1)
                signals["image_agent"] = {
                    "score": df_score,
                    "risk_level": df_result["risk_level"],
                    "details": df_result,
                }
            except Exception as e:
                logger.error("Image agent failed: {}", e)
                signals["image_agent"] = {"score": 0, "risk_level": "HIGH", "error": "Processing failed"}

        if image_path and self.liveness_detector:
            try:
                lv_result = self.liveness_detector.detect_liveness(image_path)
                lv_score = round(lv_result["liveness_score"] * 100, 1)
                risk_level = lv_result["risk_level"]
                # Active challenge: a failed head turn makes liveness CRITICAL (a static photo can't turn)
                lv_result["head_turn"] = self._check_head_turn(session, image_path, turn_image_path)
                logger.info("HEADTURN {}", lv_result["head_turn"])
                if not lv_result["head_turn"]["passed"]:
                    lv_score, risk_level = 0, "CRITICAL"
                signals["video_agent"] = {
                    "score": lv_score,
                    "risk_level": risk_level,
                    "details": lv_result,
                }
            except Exception as e:
                logger.error("Liveness agent failed: {}", e)
                signals["video_agent"] = {"score": 0, "risk_level": "HIGH", "error": "Processing failed"}

        # Run voice agent
        if audio_path and self.voice_detector:
            try:
                voice_result = self.voice_detector.detect_voice(audio_path)
                if voice_result.get("model_used") == "error":  # detector couldn't analyze the audio
                    raise ValueError("voice analysis failed")
                voice_score = round(voice_result["human_score"] * 100, 1)
                signals["voice_agent"] = {
                    "score": voice_score,
                    "risk_level": voice_result["risk_level"],
                    "details": voice_result,
                }
            except Exception as e:
                logger.error("Voice agent failed: {}", e)
                signals["voice_agent"] = {"score": 0, "risk_level": "HIGH", "error": "Processing failed"}

        # Run behavior agent
        if behavior_data and self.behavior_analyzer:
            try:
                beh_result = self.behavior_analyzer.analyze(behavior_data)
                beh_score = round(beh_result["behavior_score"] * 100, 1)
                signals["behavior_agent"] = {
                    "score": beh_score,
                    "risk_level": beh_result["risk_level"],
                    "details": beh_result,
                }
            except Exception as e:
                logger.error("Behavior agent failed: {}", e)
                signals["behavior_agent"] = {"score": 0, "risk_level": "HIGH", "error": "Processing failed"}

        # Calculate risk (only pass non-error signals to risk engine)
        clean_signals = {k: v for k, v in signals.items() if "error" not in v}
        risk_result = self.risk_engine.calculate(clean_signals)
        processing_time = round((time.time() - start) * 1000, 2)

        # Fail closed: if a check we were asked to run crashed, never auto-PASS
        failed_agents = [k for k, v in signals.items() if "error" in v]
        if failed_agents and risk_result["decision"] == "PASS":
            risk_result["decision"] = "REVIEW"
            risk_result["explanation"].append(f"Could not run: {', '.join(failed_agents)} — manual review needed")

        session_result = {
            "session_id": session_id,
            "trust_score": risk_result["trust_score"],
            "decision": risk_result["decision"],
            "explanation": risk_result["explanation"],
            "agents": risk_result["agents"],
            "overall_risk": risk_result["overall_risk"],
            "processing_time_ms": processing_time,
        }

        with self._lock:
            if session_id in self.sessions:
                session = self.sessions[session_id]
                session["status"] = "completed"
                session["agents"] = signals
                session["result"] = session_result

        logger.info("Session {}: {} (trust_score={})", session_id, risk_result["decision"], risk_result["trust_score"])
        return session_result

    def _check_head_turn(self, session: dict, front_path, turn_path) -> dict:
        """Did the user turn their head the way THIS session asked? Fails closed on anything missing."""
        asked = session["challenge"]
        result = {"asked": asked, "passed": False, "front_yaw": None, "turn_yaw": None}

        if datetime.utcnow() > datetime.fromisoformat(session["challenge_expires_at"]):
            result["reason"] = "challenge expired"
            return result
        if not turn_path:
            result["reason"] = "no turned photo"
            return result

        front_yaw = self.liveness_detector.head_yaw(front_path)
        turn_yaw = self.liveness_detector.head_yaw(turn_path)
        result["front_yaw"], result["turn_yaw"] = front_yaw, turn_yaw
        if front_yaw is None or turn_yaw is None:
            result["reason"] = "no face in one of the photos"
            return result

        result["passed"], reason = head_turn_passes(asked, front_yaw, turn_yaw)
        if reason:
            result["reason"] = reason
        return result

    def get_session_state(self, session_id: str) -> dict:
        """Get current state of a session."""
        with self._lock:
            return self.sessions.get(session_id, {"error": "Session not found"})
