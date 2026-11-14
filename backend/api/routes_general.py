"""
TrustGuard - General Routes
Landing page with interactive testing, health check.
"""

from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter(tags=["General"])

# These get set by main.py during startup
deepfake_detector_loaded = False
liveness_detector_loaded = False
voice_detector_loaded = False


# The landing page HTML lives in its own file so this file stays short.
LANDING_PAGE = (Path(__file__).parent.parent / "static" / "landing.html").read_text(encoding="utf-8")


@router.get("/", response_class=HTMLResponse)
async def root():
    """Landing page — interactive testing dashboard."""
    return LANDING_PAGE


@router.get("/health")
async def health_check():
    """Health check — shows which models are loaded."""
    return {
        "status": "healthy",
        "version": "1.0.0",
        "models_loaded": {
            "deepfake_detector": deepfake_detector_loaded,
            "liveness_detector": liveness_detector_loaded,
            "voice_detector": voice_detector_loaded,
        }
    }
