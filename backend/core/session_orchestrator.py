"""
Session Orchestrator — Manages end-to-end verification sessions.

A "session" is one verification attempt. The user submits an image,
optionally audio and behavior data, and the orchestrator:
1. Creates a session with a unique ID
2. Runs whichever agents have data (image → deepfake + liveness, audio → voice, JSON → behavior)
3. Feeds all results into the Risk Engine
4. Returns a final trust_score + decision + per-agent breakdown

Sessions are stored in-memory (dict) — simple and interview-explainable.

INTERVIEW TIP: "The orchestrator is like a project manager. It creates a session,
delegates work to each detection agent, collects their reports, and then asks
the risk engine to make the final call."
"""

import time
import uuid
from datetime import datetime
from loguru import logger


class SessionOrchestrator:
    """Coordinates multiple detection agents and produces a unified verification result."""

    def __init__(self, deepfake_detector, liveness_detector, voice_detector, behavior_analyzer, risk_engine):
        self.deepfake_detector = deepfake_detector
        self.liveness_detector = liveness_detector
        self.voice_detector = voice_detector
        self.behavior_analyzer = behavior_analyzer
        self.risk_engine = risk_engine
        self.sessions = {}  # In-memory session store
        logger.info("Session orchestrator initialized")

    def create_session(self) -> str:
        """Create a new verification session, returns session_id."""
        session_id = str(uuid.uuid4())
        self.sessions[session_id] = {
            "session_id": session_id,
            "created_at": datetime.utcnow().isoformat(),
            "status": "created",
            "agents": {},
            "result": None,
        }
        logger.info("Session created: {}", session_id)
        return session_id

    def run_session(self, session_id: str, image_path=None, audio_path=None, behavior_data=None) -> dict:
        """
        Run verification agents based on provided inputs.

        Args:
            session_id: ID from create_session()
            image_path: Path to image file (runs deepfake + liveness)
            audio_path: Path to audio file (runs voice detection)
            behavior_data: dict with keystrokes + mouse_movements

        Returns:
            Full session result with trust_score, decision, per-agent details
        """
        if session_id not in self.sessions:
            return {"error": "Session not found"}

        session = self.sessions[session_id]
        session["status"] = "processing"
        start = time.time()

        signals = {}

        # Run image agents (deepfake + liveness)
        if image_path and self.deepfake_detector:
            try:
                df_result = self.deepfake_detector.predict_image(image_path)
                # Convert to 0-100 score (higher = more trustworthy)
                df_score = round((1 - df_result["probabilities"]["fake"]) * 100, 1)
                signals["image_agent"] = {
                    "score": df_score,
                    "risk_level": df_result["risk_level"],
                    "details": df_result,
                }
                session["agents"]["image_agent"] = signals["image_agent"]
            except Exception as e:
                logger.error("Image agent failed: {}", e)
                session["agents"]["image_agent"] = {"score": 0, "risk_level": "HIGH", "error": str(e)}

        if image_path and self.liveness_detector:
            try:
                lv_result = self.liveness_detector.detect_liveness(image_path)
                lv_score = round(lv_result["liveness_score"] * 100, 1)
                signals["video_agent"] = {
                    "score": lv_score,
                    "risk_level": lv_result["risk_level"],
                    "details": lv_result,
                }
                session["agents"]["video_agent"] = signals["video_agent"]
            except Exception as e:
                logger.error("Liveness agent failed: {}", e)
                session["agents"]["video_agent"] = {"score": 0, "risk_level": "HIGH", "error": str(e)}

        # Run voice agent
        if audio_path and self.voice_detector:
            try:
                voice_result = self.voice_detector.detect_voice(audio_path)
                voice_score = round(voice_result["human_score"] * 100, 1)
                signals["voice_agent"] = {
                    "score": voice_score,
                    "risk_level": voice_result["risk_level"],
                    "details": voice_result,
                }
                session["agents"]["voice_agent"] = signals["voice_agent"]
            except Exception as e:
                logger.error("Voice agent failed: {}", e)
                session["agents"]["voice_agent"] = {"score": 0, "risk_level": "HIGH", "error": str(e)}

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
                session["agents"]["behavior_agent"] = signals["behavior_agent"]
            except Exception as e:
                logger.error("Behavior agent failed: {}", e)
                session["agents"]["behavior_agent"] = {"score": 0, "risk_level": "HIGH", "error": str(e)}

        # Calculate risk
        risk_result = self.risk_engine.calculate(signals)
        processing_time = round((time.time() - start) * 1000, 2)

        session_result = {
            "session_id": session_id,
            "trust_score": risk_result["trust_score"],
            "decision": risk_result["decision"],
            "explanation": risk_result["explanation"],
            "agents": risk_result["agents"],
            "overall_risk": risk_result["overall_risk"],
            "processing_time_ms": processing_time,
        }

        session["status"] = "completed"
        session["result"] = session_result
        logger.info("Session {}: {} (trust_score={})", session_id, risk_result["decision"], risk_result["trust_score"])

        return session_result

    def get_session_state(self, session_id: str) -> dict:
        """Get current state of a session."""
        return self.sessions.get(session_id, {"error": "Session not found"})
