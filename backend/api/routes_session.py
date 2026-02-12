"""
TrustGuard - Session Management Routes
Create verification sessions and run multi-agent verification.
"""

import json
import time

from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Request
from loguru import logger

from backend.utils.file_handling import save_temp_file, validate_image, validate_audio
from backend.utils.rate_limiter import limiter

router = APIRouter(prefix="/api/v1/session", tags=["Session"])

# Global orchestrator — set by main.py during startup
orchestrator = None
quality_gate_checker = None
audit_reporter = None


@router.post("/create")
async def create_session():
    """Create a new verification session. Returns a session_id to use in subsequent calls."""
    if orchestrator is None:
        raise HTTPException(status_code=503, detail="Session orchestrator not initialized")

    session_id = orchestrator.create_session()
    state = orchestrator.get_session_state(session_id)

    return {
        "session_id": session_id,
        "created_at": state["created_at"],
        "status": state["status"],
    }


@router.post("/{session_id}/verify")
@limiter.limit("5/minute")
async def run_verification(
    request: Request,
    session_id: str,
    image: UploadFile = File(None),
    audio: UploadFile = File(None),
    behavior_json: str = Form(None),
):
    """
    Run full multi-agent verification on a session.

    Accepts multipart form with:
    - image: selfie/photo (runs deepfake + liveness)
    - audio: voice sample (runs voice detection)
    - behavior_json: JSON string with keystroke + mouse data
    """
    if orchestrator is None:
        raise HTTPException(status_code=503, detail="Session orchestrator not initialized")

    state = orchestrator.get_session_state(session_id)
    if "error" in state:
        raise HTTPException(status_code=404, detail="Session not found")

    image_path = None
    audio_path = None
    behavior_data = None

    # We need context managers to handle temp files
    # Save files first, then run session
    import tempfile
    import shutil
    from pathlib import Path

    temp_dir = Path(tempfile.mkdtemp())

    try:
        if image:
            validate_image(image)
            img_path = temp_dir / f"image_{image.filename}"
            with img_path.open("wb") as f:
                shutil.copyfileobj(image.file, f)
            image_path = str(img_path)

        if audio:
            validate_audio(audio)
            aud_path = temp_dir / f"audio_{audio.filename}"
            with aud_path.open("wb") as f:
                shutil.copyfileobj(audio.file, f)
            audio_path = str(aud_path)

        if behavior_json:
            try:
                behavior_data = json.loads(behavior_json)
            except json.JSONDecodeError:
                raise HTTPException(status_code=400, detail="Invalid behavior_json format")

        if not image_path and not audio_path and not behavior_data:
            raise HTTPException(status_code=400, detail="At least one input required (image, audio, or behavior data)")

        result = orchestrator.run_session(
            session_id=session_id,
            image_path=image_path,
            audio_path=audio_path,
            behavior_data=behavior_data,
        )

        # Run quality gates
        if quality_gate_checker:
            from backend.core.quality_gates import QualityGateChecker
            file_hash = None
            if image_path:
                file_hash = QualityGateChecker.compute_file_hash(image_path)
            gates = quality_gate_checker.run_all_gates(result, file_hash=file_hash)
            result["quality_gates"] = gates

        # Generate audit report
        if audit_reporter:
            audit_reporter.generate_report(session_id, result)

        return result

    finally:
        # Cleanup temp files
        import shutil as sh
        sh.rmtree(temp_dir, ignore_errors=True)


@router.get("/{session_id}")
async def get_session(session_id: str):
    """Get the current state and results of a verification session."""
    if orchestrator is None:
        raise HTTPException(status_code=503, detail="Session orchestrator not initialized")

    state = orchestrator.get_session_state(session_id)
    if "error" in state:
        raise HTTPException(status_code=404, detail="Session not found")

    return state
