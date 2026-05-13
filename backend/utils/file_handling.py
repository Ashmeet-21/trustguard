"""
TrustGuard - File Handling Utilities
Handles temporary file uploads with security hardening.
"""

import uuid
import shutil
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import UploadFile, HTTPException
from backend.utils import config


UPLOAD_DIR = Path(__file__).parent.parent / "temp_uploads"

# Magic bytes for file type validation (checked against actual file content, not headers)
IMAGE_SIGNATURES = {
    b"\xff\xd8\xff": "image/jpeg",       # JPEG
    b"\x89PNG\r\n\x1a\n": "image/png",   # PNG
}
VIDEO_SIGNATURES = {
    b"\x00\x00\x00": "video/mp4",        # MP4/MOV (ftyp box)
}
AUDIO_SIGNATURES = {
    b"RIFF": "audio/wav",                 # WAV
    b"\xff\xfb": "audio/mp3",            # MP3
    b"\xff\xf3": "audio/mp3",            # MP3
    b"ID3": "audio/mp3",                 # MP3 with ID3 tag
}


def _sanitize_extension(filename: str) -> str:
    """Extract safe file extension from filename, stripping path components."""
    if not filename:
        return ".bin"
    # Take only the basename to prevent path traversal
    safe_name = Path(filename).name
    suffix = Path(safe_name).suffix.lower()
    allowed = {".jpg", ".jpeg", ".png", ".mp4", ".avi", ".mov", ".wav", ".mp3", ".m4a"}
    return suffix if suffix in allowed else ".bin"


def validate_image(file: UploadFile):
    """Check that uploaded file is an allowed image type."""
    if file.content_type not in config.ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=400,
            detail="Invalid file type. Allowed: jpg, jpeg, png"
        )


def validate_video(file: UploadFile):
    """Check that uploaded file is an allowed video type."""
    if file.content_type not in config.ALLOWED_VIDEO_TYPES:
        raise HTTPException(
            status_code=400,
            detail="Invalid file type. Allowed: mp4, avi, mov"
        )


def validate_audio(file: UploadFile):
    """Check that uploaded file is an allowed audio type."""
    if file.content_type not in config.ALLOWED_AUDIO_TYPES:
        raise HTTPException(
            status_code=400,
            detail="Invalid file type. Allowed: wav, mp3, m4a"
        )


def _check_magic_bytes(file_path: Path, signatures: dict) -> bool:
    """Validate file's magic bytes match expected type."""
    try:
        with open(file_path, "rb") as f:
            header = f.read(12)
        return any(header.startswith(sig) for sig in signatures)
    except Exception:
        return False


@asynccontextmanager
async def save_temp_file(file: UploadFile):
    """
    Save an uploaded file temporarily, yield its path, then clean up.

    Security:
    - Uses UUID filename (prevents path traversal)
    - Enforces MAX_UPLOAD_SIZE during stream
    - Validates resolved path stays within UPLOAD_DIR
    """
    UPLOAD_DIR.mkdir(exist_ok=True)
    ext = _sanitize_extension(file.filename)
    safe_name = f"{uuid.uuid4().hex}{ext}"
    temp_path = UPLOAD_DIR / safe_name

    # Verify path stays within upload directory
    if not str(temp_path.resolve()).startswith(str(UPLOAD_DIR.resolve())):
        raise HTTPException(status_code=400, detail="Invalid file path")

    try:
        # Stream with size limit enforcement
        bytes_written = 0
        with temp_path.open("wb") as buffer:
            while True:
                chunk = file.file.read(8192)
                if not chunk:
                    break
                bytes_written += len(chunk)
                if bytes_written > config.MAX_UPLOAD_SIZE:
                    buffer.close()
                    if temp_path.exists():
                        temp_path.unlink()
                    raise HTTPException(
                        status_code=413,
                        detail=f"File too large. Maximum size: {config.MAX_UPLOAD_SIZE // (1024*1024)}MB"
                    )
                buffer.write(chunk)
        yield temp_path
    finally:
        if temp_path.exists():
            temp_path.unlink()
