"""
TrustGuard - Liveness Detection Routes
Image and video liveness detection endpoints.
"""

import time

import cv2
import numpy as np
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Request
from sqlalchemy.orm import Session
from loguru import logger

from backend.database.session import get_db
from backend.database.models import VerificationLog
from backend.utils.file_handling import save_temp_file, validate_image, validate_video
from backend.utils.rate_limiter import limiter

router = APIRouter(prefix="/api/v1/detect", tags=["Liveness Detection"])

# Global detector — set by main.py during startup
detector = None


@router.post("/liveness")
@limiter.limit("10/minute")
async def detect_liveness_image(
    request: Request,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """Detect if an uploaded image shows a live person vs a spoof attack."""
    if detector is None:
        raise HTTPException(status_code=503, detail="Liveness detector not initialized")

    validate_image(file)

    async with save_temp_file(file) as temp_path:
        start = time.time()
        result = detector.detect_liveness(str(temp_path))
        result["processing_time_ms"] = round((time.time() - start) * 1000, 2)

    # Save to database
    log = VerificationLog(
        verification_type="liveness_image",
        filename=file.filename,
        result_json=result,
        is_deepfake=not result["is_live"],  # spoof = deepfake equivalent
        confidence=result["liveness_score"],
        risk_level=result["risk_level"],
        processing_time_ms=result["processing_time_ms"],
    )
    db.add(log)
    db.commit()

    logger.info("Liveness: {} (score={:.4f})", result["classification"], result["liveness_score"])
    return result


@router.post("/liveness/video")
@limiter.limit("5/minute")
async def detect_liveness_video(
    request: Request,
    file: UploadFile = File(...),
    sample_frames: int = 10,
    db: Session = Depends(get_db),
):
    """Analyze video for liveness by sampling frames (majority vote)."""
    if detector is None:
        raise HTTPException(status_code=503, detail="Liveness detector not initialized")

    validate_video(file)

    async with save_temp_file(file) as temp_path:
        start = time.time()

        cap = cv2.VideoCapture(str(temp_path))
        if not cap.isOpened():
            raise HTTPException(status_code=400, detail="Could not open video file")

        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        if total_frames == 0:
            cap.release()
            raise HTTPException(status_code=400, detail="Video has no frames")

        frame_indices = np.linspace(0, total_frames - 1, min(sample_frames, total_frames), dtype=int)

        frame_results = []
        for idx in frame_indices:
            cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
            ret, frame = cap.read()
            if not ret:
                continue
            result = detector.detect_liveness(frame)
            frame_results.append(result)

        cap.release()

        # Majority vote
        live_count = sum(1 for r in frame_results if r["is_live"])
        avg_score = float(np.mean([r["liveness_score"] for r in frame_results])) if frame_results else 0.0
        is_live = live_count > len(frame_results) * 0.5

        video_result = {
            "is_live": bool(is_live),
            "liveness_score": round(avg_score, 4),
            "frames_analyzed": len(frame_results),
            "live_frames": int(live_count),
            "live_percentage": round(live_count / len(frame_results) * 100, 2) if frame_results else 0.0,
            "risk_level": detector._get_risk_level(avg_score),
            "classification": "LIVE" if is_live else "SPOOF",
            "frame_results": frame_results[:5],  # First 5 as sample
            "processing_time_ms": round((time.time() - start) * 1000, 2),
        }

    # Save to database
    log = VerificationLog(
        verification_type="liveness_video",
        filename=file.filename,
        result_json=video_result,
        is_deepfake=not video_result["is_live"],
        confidence=video_result["liveness_score"],
        risk_level=video_result["risk_level"],
        processing_time_ms=video_result["processing_time_ms"],
    )
    db.add(log)
    db.commit()

    logger.info("Liveness video: {} ({} frames)", video_result["classification"], video_result["frames_analyzed"])
    return video_result
