"""
TrustGuard API - Main FastAPI Application
Entry point that sets up the app, registers routes, and initializes models.
"""

import sys
import os
os.environ["PYTHONUTF8"] = "1"
if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
import uvicorn
from loguru import logger

from backend.utils import config
from backend.utils.logging import setup_logging
from backend.core.deepfake_detector import DeepfakeDetector
from backend.core.liveness_detector import LivenessDetector
from backend.core.hf_gateway import HFGateway
from backend.core.voice_detector import VoiceDetector
from backend.core.behavior_analyzer import BehaviorAnalyzer
from backend.core.risk_engine import RiskEngine
from backend.core.session_orchestrator import SessionOrchestrator
from backend.core.quality_gates import QualityGateChecker
from backend.core.audit_reporter import AuditReporter
from backend.database.models import Base
from backend.database.session import engine
from backend.utils.rate_limiter import limiter

# Import routers
from backend.api import routes_general, routes_deepfake, routes_liveness, routes_voice, routes_behavior, routes_session, routes_audit, routes_kyc, routes_auth, routes_user, routes_analytics


# ── Security Headers Middleware ─────────────────────────────────
class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Adds security headers to every response."""
    async def dispatch(self, request: Request, call_next):
        response: Response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        if not config.DEBUG:
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        # Prevent caching of authenticated responses
        if "authorization" in {k.lower() for k in request.headers.keys()}:
            response.headers["Cache-Control"] = "no-store"
        return response


@asynccontextmanager
async def lifespan(app):
    """Startup: initialize logging, database, and ML models."""
    setup_logging()
    logger.info("Starting TrustGuard API...")

    # Create database tables
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables ready")

    # Initialize deepfake detector
    try:
        detector = DeepfakeDetector(model_path=config.DEEPFAKE_MODEL_PATH)
    except Exception as e:
        logger.warning("Could not load trained model: {}. Using default weights.", e)
        detector = DeepfakeDetector()

    # Make detector available to routes
    routes_deepfake.detector = detector
    routes_general.deepfake_detector_loaded = True
    logger.info("Deepfake detector initialized")

    # Initialize liveness detector
    liveness_detector = LivenessDetector()
    routes_liveness.detector = liveness_detector
    routes_general.liveness_detector_loaded = True
    logger.info("Liveness detector initialized")

    # Initialize HF Gateway + Voice Detector
    hf_gateway = HFGateway()
    voice_detector = VoiceDetector(hf_gateway)
    routes_voice.detector = voice_detector
    routes_general.voice_detector_loaded = True
    logger.info("Voice detector initialized")

    # Initialize Behavior Analyzer
    behavior_analyzer = BehaviorAnalyzer()
    routes_behavior.analyzer = behavior_analyzer
    logger.info("Behavior analyzer initialized")

    # Initialize Risk Engine + Session Orchestrator
    risk_engine = RiskEngine()
    session_orchestrator = SessionOrchestrator(
        deepfake_detector=detector,
        liveness_detector=liveness_detector,
        voice_detector=voice_detector,
        behavior_analyzer=behavior_analyzer,
        risk_engine=risk_engine,
    )
    routes_session.orchestrator = session_orchestrator
    logger.info("Session orchestrator initialized")

    # Initialize Quality Gates + Audit Reporter
    quality_gate_checker = QualityGateChecker()
    audit_reporter = AuditReporter()
    routes_session.quality_gate_checker = quality_gate_checker
    routes_session.audit_reporter = audit_reporter
    routes_audit.reporter = audit_reporter
    logger.info("Quality gates and audit reporter initialized")

    # Wire up KYC pipeline — it uses both detectors
    routes_kyc.deepfake_detector = detector
    routes_kyc.liveness_detector = liveness_detector
    routes_kyc.risk_engine = risk_engine
    logger.info("KYC pipeline ready")

    logger.info("TrustGuard API ready! Docs at http://{}:{}/docs", config.API_HOST, config.API_PORT)

    try:
        yield
    finally:
        # Cleanup: dispose database engine to release connections
        logger.info("Shutting down — disposing database engine...")
        engine.dispose()
        logger.info("Database engine disposed")


# Tag metadata — controls how endpoint groups appear in Swagger UI
tags_metadata = [
    {
        "name": "KYC Verification",
        "description": "Full verification pipeline — runs deepfake + liveness checks and returns a **PASS / FAIL / REVIEW** verdict.",
    },
    {
        "name": "Deepfake Detection",
        "description": "Detect AI-generated or manipulated images and videos using a Vision Transformer (ViT) model.",
    },
    {
        "name": "Liveness Detection",
        "description": "Detect spoof attacks (printed photos, screen replays, masks) using 6 independent image checks.",
    },
    {
        "name": "Voice Detection",
        "description": "Detect AI-generated or cloned voice audio using HuggingFace API with local spectral fallback.",
    },
    {
        "name": "Behavior Detection",
        "description": "Detect bots using keystroke timing and mouse movement pattern analysis.",
    },
    {
        "name": "Session",
        "description": "Create and manage multi-agent verification sessions.",
    },
    {
        "name": "Audit",
        "description": "Audit reports and verification history for compliance.",
    },
    {
        "name": "Analytics",
        "description": "Platform usage statistics and recent verification activity.",
    },
    {
        "name": "Authentication",
        "description": "Register and login to get a JWT token for authenticated endpoints.",
    },
    {
        "name": "User",
        "description": "User profile and verification history (requires JWT token).",
    },
    {
        "name": "General",
        "description": "Health check and system status.",
    },
]

# Create FastAPI app — disable docs in production
app = FastAPI(
    title="TrustGuard",
    description="""
## Multi-Modal Identity Verification API

TrustGuard combines **deepfake detection**, **liveness verification**, and a **KYC pipeline** into a single API.

### How it works
1. **Upload an image** to any detection endpoint
2. The system runs AI-powered checks (deepfake model + 6 liveness signals)
3. Get back a detailed result with confidence scores and risk levels

### Key Endpoints
| Endpoint | What it does |
|----------|-------------|
| `POST /api/v1/verify/kyc` | Full KYC — runs both checks, returns PASS/FAIL/REVIEW |
| `POST /api/v1/detect/deepfake/image` | Is this image AI-generated? |
| `POST /api/v1/detect/liveness` | Is this a live person or a spoof? |
| `GET /api/v1/analytics/summary` | Platform usage stats |

### Rate Limits
Detection endpoints are rate-limited per IP (10/min for images, 5/min for video, 3/min for batch).

---
*Built with FastAPI, OpenCV, MediaPipe, and HuggingFace Transformers*
""",
    version=config.APP_VERSION,
    lifespan=lifespan,
    openapi_tags=tags_metadata,
    docs_url="/docs" if config.DEBUG else None,
    redoc_url="/redoc" if config.DEBUG else None,
    openapi_url="/openapi.json" if config.DEBUG else None,
)

# Security headers
app.add_middleware(SecurityHeadersMiddleware)

# Rate limiting — prevents API abuse (e.g., 10 requests/minute per IP)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS — explicit method and header whitelist
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "Accept"],
)

# Register all route groups
app.include_router(routes_general.router)
app.include_router(routes_deepfake.router)
app.include_router(routes_liveness.router)
app.include_router(routes_voice.router)
app.include_router(routes_behavior.router)
app.include_router(routes_session.router)
app.include_router(routes_audit.router)
app.include_router(routes_kyc.router)
app.include_router(routes_auth.router)
app.include_router(routes_user.router)
app.include_router(routes_analytics.router)


if __name__ == "__main__":
    uvicorn.run(
        "backend.main:app",
        host=config.API_HOST,
        port=config.API_PORT,
        reload=config.DEBUG,
        log_level=config.LOG_LEVEL.lower(),
    )
