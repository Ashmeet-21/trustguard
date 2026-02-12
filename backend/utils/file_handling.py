"""
TrustGuard - File Handling Utilities
Handles temporary file uploads and cleanup.
"""

import shutil
from pathlib import Path
from datetime import datetime
from contextlib import asynccontextmanager
from fastapi import UploadFile, HTTPException
from backend.utils import config


UPLOAD_DIR = Path(__file__).parent.parent / "temp_uploads"


def validate_image(file: UploadFile):
    """Check that uploaded file is an allowed image type."""
    if file.content_type not in config.ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type '{file.content_type}'. Allowed: jpg, jpeg, png"
        )


def validate_video(file: UploadFile):
    """Check that uploaded file is an allowed video type."""
    if file.content_type not in config.ALLOWED_VIDEO_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type '{file.content_type}'. Allowed: mp4, avi, mov"
        )


def validate_audio(file: UploadFile):
    """Check that uploaded file is an allowed audio type."""
    if file.content_type not in config.ALLOWED_AUDIO_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type '{file.content_type}'. Allowed: wav, mp3, m4a"
        )


@asynccontextmanager
async def save_temp_file(file: UploadFile):
    """
    Save an uploaded file temporarily, yield its path, then clean up.

    Usage:
        async with save_temp_file(file) as temp_path:
            result = detector.predict_image(str(temp_path))
    """
    UPLOAD_DIR.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    temp_path = UPLOAD_DIR / f"{timestamp}_{file.filename}"

    try:
        with temp_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        yield temp_path
    finally:
        if temp_path.exists():
            temp_path.unlink()
