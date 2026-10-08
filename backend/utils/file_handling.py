"""
TrustGuard - File Handling Utilities
Handles temporary file uploads with security hardening.
"""

import uuid
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import UploadFile, HTTPException
from backend.utils import config


UPLOAD_DIR = Path(__file__).parent.parent / "temp_uploads"

def _looks_like(kind: str, header: bytes) -> bool:
    """
    Check the file's first bytes ("magic bytes") match the expected kind.
    The Content-Type header is set by the client and can lie — the file content can't.
    """
    is_mp4_family = header[4:8] == b"ftyp"   # MP4 / MOV / M4A all start with an 'ftyp' box
    if kind == "image":
        return header.startswith(b"\xff\xd8\xff") or header.startswith(b"\x89PNG\r\n\x1a\n")
    if kind == "video":
        return is_mp4_family or header.startswith(b"RIFF")          # RIFF = AVI
    if kind == "audio":
        return (header.startswith(b"RIFF")                           # WAV
                or header.startswith(b"ID3")                         # MP3 with tag
                or header[:2] in (b"\xff\xfb", b"\xff\xf3", b"\xff\xf2")  # MP3
                or is_mp4_family)                                    # M4A
    return False


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


@asynccontextmanager
async def save_temp_file(file: UploadFile, kind: str):
    """
    Save an uploaded file temporarily, yield its path, then clean up.

    kind: "image", "video" or "audio" — the file content must match it.

    Security:
    - Uses UUID filename (prevents path traversal)
    - Enforces MAX_UPLOAD_SIZE during stream
    - Validates resolved path stays within UPLOAD_DIR
    - Checks magic bytes so a renamed/mislabelled file is rejected
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

        with temp_path.open("rb") as f:
            header = f.read(12)
        if not _looks_like(kind, header):
            raise HTTPException(status_code=400, detail=f"File content is not a valid {kind}")

        yield temp_path
    finally:
        if temp_path.exists():
            temp_path.unlink()
