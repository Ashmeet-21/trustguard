"""
TrustGuard - Deepfake Detection Routes
Image, video, and batch deepfake detection endpoints.
"""

import time
from typing import List, Optional

from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Request
from sqlalchemy.orm import Session
from loguru import logger

from backend.database.session import get_db
from backend.database.models import VerificationLog
from backend.utils.file_handling import save_temp_file, validate_image, validate_video
from backend.utils.rate_limiter import limiter

router = APIRouter(prefix="/api/v1/detect", tags=["Deepfake Detection"])

# Global detector — set by main.py during startup
detector = None


@router.post("/deepfake/image")
@limiter.limit("10/minute")
async def detect_deepfake_image(
    request: Request,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """Detect if an uploaded image is a deepfake."""
    if detector is None:
        raise HTTPException(status_code=503, detail="Deepfake detector not initialized")

    validate_image(file)

    async with save_temp_file(file) as temp_path:
        start = time.time()
        result = detector.predict_image(str(temp_path))
        result["processing_time_ms"] = round((time.time() - start) * 1000, 2)

    # Save to database
    log = VerificationLog(
        verification_type="deepfake_image",
        filename=file.filename,
        result_json=result,
        is_deepfake=result["is_deepfake"],
        confidence=result["confidence"],
        risk_level=result["risk_level"],
        processing_time_ms=result["processing_time_ms"],
    )
    db.add(log)
    db.commit()

    logger.info("Image: {} (confidence={:.2f})", result["classification"], result["confidence"])
    return result


@router.post("/deepfake/video")
@limiter.limit("5/minute")
async def detect_deepfake_video(
    request: Request,
    file: UploadFile = File(...),
    sample_frames: int = 30,  # Bounded in route to 1-100
    db: Session = Depends(get_db),
):
    """Detect deepfake frames in an uploaded video."""
    if detector is None:
        raise HTTPException(status_code=503, detail="Deepfake detector not initialized")

    validate_video(file)
    sample_frames = max(1, min(100, sample_frames))  # Clamp to safe range

    async with save_temp_file(file) as temp_path:
        start = time.time()
        result = detector.predict_video(str(temp_path), sample_frames)
        result["processing_time_ms"] = round((time.time() - start) * 1000, 2)

    log = VerificationLog(
        verification_type="deepfake_video",
        filename=file.filename,
        result_json=result,
        is_deepfake=result["is_deepfake"],
        confidence=result["confidence"],
        risk_level=result["risk_level"],
        processing_time_ms=result["processing_time_ms"],
    )
    db.add(log)
    db.commit()

    logger.info("Video: {} ({} frames)", result["classification"], result["frames_analyzed"])
    return result


@router.post("/batch")
@limiter.limit("3/minute")
async def detect_batch(
    request: Request,
    files: List[UploadFile] = File(...),
    db: Session = Depends(get_db),
):
    """Batch deepfake detection for multiple images (max 10)."""
    if detector is None:
        raise HTTPException(status_code=503, detail="Deepfake detector not initialized")

    if len(files) > 10:
        raise HTTPException(status_code=400, detail="Maximum 10 files per batch")

    results = []
    for file in files:
        try:
            async with save_temp_file(file) as temp_path:
                result = detector.predict_image(str(temp_path))
                result["filename"] = file.filename
                results.append(result)
        except Exception as e:
            logger.error("Batch processing failed for {}: {}", file.filename, e)
            results.append({"filename": file.filename, "error": "Processing failed", "is_deepfake": None})

    summary = {
        "deepfakes_detected": sum(1 for r in results if r.get("is_deepfake") is True),
        "real_images": sum(1 for r in results if r.get("is_deepfake") is False),
        "errors": sum(1 for r in results if "error" in r),
    }

    # Log batch to database
    log = VerificationLog(
        verification_type="batch",
        result_json={"total_files": len(files), "summary": summary},
        is_deepfake=summary["deepfakes_detected"] > 0,
    )
    db.add(log)
    db.commit()

    return {"total_files": len(files), "results": results, "summary": summary}
