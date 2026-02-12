"""
TrustGuard - Behavioral Biometrics Routes
Accepts JSON keystroke + mouse data and analyzes for bot-like patterns.
"""

import time

from fastapi import APIRouter, HTTPException, Request
from loguru import logger

from backend.api.schemas import BehaviorRequest
from backend.utils.rate_limiter import limiter

router = APIRouter(prefix="/api/v1/detect", tags=["Behavior Detection"])

# Global analyzer — set by main.py during startup
analyzer = None


@router.post("/behavior")
@limiter.limit("10/minute")
async def detect_behavior(
    request: Request,
    payload: BehaviorRequest,
):
    """
    Analyze keystroke and mouse movement data for bot-like behavior.

    Accepts JSON body (not file upload) with keystroke timings and mouse movements.
    Returns a behavior score and HUMAN/BOT classification.
    """
    if analyzer is None:
        raise HTTPException(status_code=503, detail="Behavior analyzer not initialized")

    start = time.time()

    data = {
        "keystrokes": [k.model_dump() for k in payload.keystrokes],
        "mouse_movements": [m.model_dump() for m in payload.mouse_movements],
    }

    result = analyzer.analyze(data)
    result["processing_time_ms"] = round((time.time() - start) * 1000, 2)

    logger.info("Behavior: {} (score={:.4f})", result["classification"], result["behavior_score"])
    return result
