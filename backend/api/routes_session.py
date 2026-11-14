"""
TrustGuard - Session Management Routes
Create verification sessions and run multi-agent verification.
"""

import json
from contextlib import AsyncExitStack

from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Request, Depends
from sqlalchemy.orm import Session as DBSession
from loguru import logger

from backend.api.schemas import BehaviorRequest
from backend.api.routes_user import get_optional_user
from backend.core.quality_gates import QualityGateChecker
from backend.database.session import get_db
from backend.database.models import User, VerificationLog
from backend.utils.file_handling import save_temp_file, validate_image, validate_audio
from backend.utils.rate_limiter import limiter

router = APIRouter(prefix="/api/v1/session", tags=["Session"])

# Global orchestrator — set by main.py during startup
orchestrator = None
quality_gate_checker = None
audit_reporter = None


@router.post("/create")
@limiter.limit("10/minute")
async def create_session(request: Request, current_user: User | None = Depends(get_optional_user)):
    """Create a new verification session. Returns a session_id to use in subsequent calls."""
    if orchestrator is None:
        raise HTTPException(status_code=503, detail="Session orchestrator not initialized")

    session_id = orchestrator.create_session(user_id=current_user.id if current_user else None)
    state = orchestrator.get_session_state(session_id)

    return {
        "session_id": session_id,
        "created_at": state["created_at"],
        "status": state["status"],
        "challenge": state["challenge"],
        "user_id": current_user.id if current_user else None,
    }


def _parse_behavior(behavior_json):
    """Turn the behavior_json form field into a checked dict (None if not sent). Bad input -> 400."""
    if not behavior_json:
        return None
    try:
        return BehaviorRequest(**json.loads(behavior_json)).model_dump()
    except (ValueError, TypeError):  # bad JSON or failed schema validation
        raise HTTPException(status_code=400, detail="Invalid behavior_json format")


async def _save_optional(stack, upload, kind):
    """Save one optional upload with save_temp_file; returns its path, or None if it wasn't sent."""
    if not upload:
        return None
    return str(await stack.enter_async_context(save_temp_file(upload, kind)))


@router.post("/{session_id}/verify")
@limiter.limit("5/minute")
async def run_verification(
    request: Request,
    session_id: str,
    image: UploadFile = File(None),
    turn_image: UploadFile = File(None),
    audio: UploadFile = File(None),
    behavior_json: str = Form(None),
    current_user: User | None = Depends(get_optional_user),
    db: DBSession = Depends(get_db),
):
    """
    Run full multi-agent verification on a session.

    Accepts multipart form with:
    - image: selfie/photo (runs deepfake + liveness)
    - turn_image: second photo with the head turned the way the session asked (challenge)
    - audio: voice sample (runs voice detection)
    - behavior_json: JSON string with keystroke + mouse data
    """
    if orchestrator is None:
        raise HTTPException(status_code=503, detail="Session orchestrator not initialized")

    _get_owned_session(session_id, current_user)

    behavior_data = _parse_behavior(behavior_json)

    if not image and not audio and not behavior_data:
        raise HTTPException(status_code=400, detail="At least one input required (image, audio, or behavior data)")
    if image:
        validate_image(image)
    if turn_image:
        validate_image(turn_image)
    if audio:
        validate_audio(audio)

    # Save the uploads (size limit + content check). The stack deletes them all when the block ends.
    async with AsyncExitStack() as stack:
        image_path = await _save_optional(stack, image, "image")
        turn_path = await _save_optional(stack, turn_image, "image")
        audio_path = await _save_optional(stack, audio, "audio")

        try:
            result = orchestrator.run_session(
                session_id=session_id,
                image_path=image_path,
                audio_path=audio_path,
                turn_image_path=turn_path,
                behavior_data=behavior_data,
            )
            if "error" in result:
                raise HTTPException(status_code=409, detail=result["error"])

            # Quality gates run after the agents and can make the decision stricter
            if quality_gate_checker:
                file_hash = QualityGateChecker.compute_file_hash(image_path) if image_path else None
                gates = quality_gate_checker.run_all_gates(result, file_hash=file_hash)
                result["quality_gates"] = gates
                quality_gate_checker.apply_gates(result, gates)
        except HTTPException:
            raise
        except Exception as e:
            logger.error("Verification failed for session {}: {}", session_id, e)
            raise HTTPException(status_code=500, detail="Verification processing failed")

    if audit_reporter:
        audit_reporter.generate_report(session_id, result, user_id=current_user.id if current_user else None)

    # Link verification to user if authenticated
    if current_user:
        db.add(VerificationLog(
            user_id=current_user.id,
            verification_type="session",
            result_json=result,
            risk_level=result.get("overall_risk", "UNKNOWN"),
            processing_time_ms=result.get("processing_time_ms", 0),
        ))
        db.commit()

    return result


@router.get("/{session_id}")
async def get_session(session_id: str, current_user: User | None = Depends(get_optional_user)):
    """Get the current state and results of a verification session."""
    if orchestrator is None:
        raise HTTPException(status_code=503, detail="Session orchestrator not initialized")

    return _get_owned_session(session_id, current_user)


def _get_owned_session(session_id: str, current_user: User | None) -> dict:
    """
    Return the session, or 404 if it doesn't exist or belongs to someone else.
    (404 instead of 403 so we don't confirm that someone else's session exists.)
    Anonymous sessions (no owner) are usable by whoever holds the random session_id.
    """
    state = orchestrator.get_session_state(session_id)
    owner = state.get("user_id")
    if "error" in state or (owner is not None and (current_user is None or current_user.id != owner)):
        raise HTTPException(status_code=404, detail="Session not found")
    return state
