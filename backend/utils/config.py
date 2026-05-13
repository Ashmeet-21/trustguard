"""
TrustGuard - Configuration
Loads settings from .env file using python-dotenv.
"""

import os
import secrets
from pathlib import Path
from dotenv import load_dotenv

# Load .env from project root
env_path = Path(__file__).parent.parent.parent / ".env"
load_dotenv(env_path)


# Application
APP_NAME = os.getenv("APP_NAME", "TrustGuard")
APP_VERSION = os.getenv("APP_VERSION", "1.0.0")
DEBUG = os.getenv("DEBUG", "False").lower() == "true"

# Generate cryptographically secure defaults — never use hardcoded secrets
SECRET_KEY = os.getenv("SECRET_KEY") or secrets.token_urlsafe(32)
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY") or secrets.token_urlsafe(32)

# API
API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", "8000"))
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:8000").split(",")

# Database
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./trustguard.db")

# Model Paths
DEEPFAKE_MODEL_PATH = os.getenv("DEEPFAKE_MODEL_PATH", "backend/models/deepfake_detector.pth")
LIVENESS_MODEL_PATH = os.getenv("LIVENESS_MODEL_PATH", "backend/models/liveness_detector.h5")
VOICE_MODEL_PATH = os.getenv("VOICE_MODEL_PATH", "backend/models/voice_detector.h5")

# Detection Thresholds (clamped to valid range)
DEEPFAKE_THRESHOLD = max(0.0, min(1.0, float(os.getenv("DEEPFAKE_THRESHOLD", "0.5"))))
LIVENESS_THRESHOLD = max(0.0, min(1.0, float(os.getenv("LIVENESS_THRESHOLD", "0.7"))))
VOICE_THRESHOLD = max(0.0, min(1.0, float(os.getenv("VOICE_THRESHOLD", "0.6"))))

# File Upload
MAX_UPLOAD_SIZE = int(os.getenv("MAX_UPLOAD_SIZE", "10485760"))  # 10MB
ALLOWED_IMAGE_TYPES = ["image/jpeg", "image/jpg", "image/png"]
ALLOWED_VIDEO_TYPES = ["video/mp4", "video/avi", "video/quicktime"]
ALLOWED_AUDIO_TYPES = ["audio/wav", "audio/mp3", "audio/m4a"]

# JWT / Security
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))

# HuggingFace Inference API
HF_TOKEN = os.getenv("HF_TOKEN", "")
HF_VOICE_MODEL = os.getenv("HF_VOICE_MODEL", "MattyB95/AST-ASVspoof2019-Synthetic-Voice-Detection")
HF_IMAGE_MODEL = os.getenv("HF_IMAGE_MODEL", "dima806/deepfake_vs_real_image_detection")

# Behavior Analysis
BEHAVIOR_THRESHOLD = float(os.getenv("BEHAVIOR_THRESHOLD", "0.6"))

# Logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FILE = os.getenv("LOG_FILE", "logs/trustguard.log")
