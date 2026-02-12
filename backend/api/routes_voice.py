"""
TrustGuard - Voice Deepfake Detection Routes
Audio upload endpoints for synthetic voice detection.
"""

import time
from typing import List

from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Request
from sqlalchemy.orm import Session
from loguru import logger

from backend.database.session import get_db
from backend.database.models import VerificationLog
from backend.utils.file_handling import save_temp_file, validate_audio
from backend.utils.rate_limiter import limiter

router = APIRouter(prefix="/api/v1/detect", tags=["Voice Detection"])

# Global detector — set by main.py during startup
detector = None


@router.post("/voice")
@limiter.limit("10/minute")
async def detect_voice(
    request: Request,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """Detect if an uploaded audio file contains synthetic/AI-generated voice."""
    if detector is None:
        raise HTTPException(status_code=503, detail="Voice detector not initialized")

    validate_audio(file)

    async with save_temp_file(file) as temp_path:
        result = detector.detect_voice(str(temp_path))

    # Save to database
    log = VerificationLog(
        verification_type="voice",
        filename=file.filename,
        result_json=result,
        is_deepfake=result["is_synthetic"],
        confidence=result["confidence"],
        risk_level=result["risk_level"],
        processing_time_ms=result["processing_time_ms"],
    )
    db.add(log)
    db.commit()

    logger.info("Voice: {} (confidence={:.2f})", result["classification"], result["confidence"])
    return result


@router.post("/voice/batch")
@limiter.limit("3/minute")
async def detect_voice_batch(
    request: Request,
    files: List[UploadFile] = File(...),
    db: Session = Depends(get_db),
):
    """Batch voice detection for multiple audio files (max 5)."""
    if detector is None:
        raise HTTPException(status_code=503, detail="Voice detector not initialized")

    if len(files) > 5:
        raise HTTPException(status_code=400, detail="Maximum 5 files per batch")

    results = []
    for file in files:
        try:
            validate_audio(file)
            async with save_temp_file(file) as temp_path:
                result = detector.detect_voice(str(temp_path))
                result["filename"] = file.filename
                results.append(result)
        except Exception as e:
            results.append({"filename": file.filename, "error": str(e), "is_synthetic": None})

    summary = {
        "synthetic_detected": sum(1 for r in results if r.get("is_synthetic") is True),
        "human_audio": sum(1 for r in results if r.get("is_synthetic") is False),
        "errors": sum(1 for r in results if "error" in r),
    }

    log = VerificationLog(
        verification_type="voice_batch",
        result_json={"total_files": len(files), "summary": summary},
        is_deepfake=summary["synthetic_detected"] > 0,
    )
    db.add(log)
    db.commit()

    return {"total_files": len(files), "results": results, "summary": summary}
