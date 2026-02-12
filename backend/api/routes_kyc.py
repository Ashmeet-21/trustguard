"""
TrustGuard - KYC Verification Pipeline

KYC = "Know Your Customer" — banks/fintech use this to verify someone is real.

This endpoint runs BOTH checks on one image:
1. Deepfake check — is this image AI-generated?
2. Liveness check — is this a live person or a photo/screen?

Then combines the results into a single PASS / FAIL / REVIEW decision.

WHY one endpoint instead of calling both separately?
- Real KYC systems run multiple checks in one go
- The user uploads once, gets a full verdict
- Shows we can build a pipeline that orchestrates multiple services
"""

import time

from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Request
from sqlalchemy.orm import Session
from loguru import logger

from backend.database.session import get_db
from backend.database.models import VerificationLog
from backend.utils.file_handling import save_temp_file, validate_image
from backend.utils.rate_limiter import limiter

router = APIRouter(prefix="/api/v1/verify", tags=["KYC Verification"])

# These get set by main.py during startup
deepfake_detector = None
liveness_detector = None
risk_engine = None


@router.post("/kyc")
@limiter.limit("5/minute")
async def verify_kyc(
    request: Request,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """
    Full KYC verification — one image, two checks, one verdict.

    Returns PASS, FAIL, or REVIEW based on combined results:
    - PASS:   Image is real AND person is live
    - FAIL:   Image is fake OR person is clearly a spoof
    - REVIEW: Results are borderline, needs human review
    """
    if deepfake_detector is None or liveness_detector is None:
        raise HTTPException(status_code=503, detail="Detectors not initialized")

    validate_image(file)

    async with save_temp_file(file) as temp_path:
        start = time.time()

        # Run both checks on the same image
        deepfake_result = deepfake_detector.predict_image(str(temp_path))
        liveness_result = liveness_detector.detect_liveness(str(temp_path))

        processing_time = round((time.time() - start) * 1000, 2)

    # ── Decision Logic ──────────────────────────────────
    # Simple rules anyone can explain in an interview:
    #
    # FAIL if:  deepfake detected  OR  liveness score very low (< 0.4)
    # PASS if:  not a deepfake     AND  liveness score high (>= 0.7)
    # REVIEW:   everything else (borderline cases)

    is_deepfake = deepfake_result["is_deepfake"]
    liveness_score = liveness_result["liveness_score"]

    if is_deepfake or liveness_score < 0.4:
        verdict = "FAIL"
        reason = "Deepfake detected" if is_deepfake else "Low liveness score"
    elif not is_deepfake and liveness_score >= 0.7:
        verdict = "PASS"
        reason = "Image appears authentic and live"
    else:
        verdict = "REVIEW"
        reason = "Borderline results — manual review recommended"

    # Combine risk levels — take the worse one
    risk_order = {"LOW": 0, "MEDIUM": 1, "HIGH": 2, "CRITICAL": 3}
    deepfake_risk = risk_order.get(deepfake_result["risk_level"], 0)
    liveness_risk = risk_order.get(liveness_result["risk_level"], 0)
    worst_risk = max(deepfake_risk, liveness_risk)
    overall_risk = [k for k, v in risk_order.items() if v == worst_risk][0]

    # Calculate trust_score via risk engine if available
    trust_score = None
    explanation = None
    if risk_engine:
        df_score = round((1 - deepfake_result["probabilities"]["fake"]) * 100, 1)
        lv_score = round(liveness_result["liveness_score"] * 100, 1)
        risk_result = risk_engine.calculate({
            "image_agent": {"score": df_score, "risk_level": deepfake_result["risk_level"]},
            "video_agent": {"score": lv_score, "risk_level": liveness_result["risk_level"]},
        })
        trust_score = risk_result["trust_score"]
        explanation = risk_result["explanation"]

    result = {
        "verdict": verdict,
        "reason": reason,
        "overall_risk": overall_risk,
        "trust_score": trust_score,
        "explanation": explanation,
        "deepfake_check": {
            "is_deepfake": deepfake_result["is_deepfake"],
            "confidence": deepfake_result["confidence"],
            "classification": deepfake_result["classification"],
            "risk_level": deepfake_result["risk_level"],
        },
        "liveness_check": {
            "is_live": liveness_result["is_live"],
            "liveness_score": liveness_result["liveness_score"],
            "classification": liveness_result["classification"],
            "risk_level": liveness_result["risk_level"],
            "checks": liveness_result["checks"],
        },
        "processing_time_ms": processing_time,
    }

    # Save to database
    log = VerificationLog(
        verification_type="kyc",
        filename=file.filename,
        result_json=result,
        is_deepfake=is_deepfake,
        confidence=deepfake_result["confidence"],
        risk_level=overall_risk,
        processing_time_ms=processing_time,
    )
    db.add(log)
    db.commit()

    logger.info("KYC: {} — deepfake={}, liveness={:.4f}", verdict, is_deepfake, liveness_score)
    return result
