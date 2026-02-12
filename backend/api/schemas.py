"""
TrustGuard - API Request/Response Schemas
Pydantic models for input validation and output serialization.
"""

from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, List, Dict
from datetime import datetime


# ── General ──────────────────────────────────────────────

class HealthResponse(BaseModel):
    status: str
    version: str
    models_loaded: Dict[str, bool]


# ── Deepfake Detection ──────────────────────────────────

class DeepfakeImageResponse(BaseModel):
    is_deepfake: bool
    confidence: float
    classification: str       # "REAL" or "FAKE"
    risk_level: str            # "LOW", "MEDIUM", "HIGH", "CRITICAL"
    probabilities: Dict[str, float]
    processing_time_ms: float


class DeepfakeVideoResponse(BaseModel):
    is_deepfake: bool
    confidence: float
    frames_analyzed: int
    fake_frames: int
    fake_percentage: float
    classification: str
    risk_level: str
    frame_predictions: List[Dict]
    processing_time_ms: float


class BatchResultItem(BaseModel):
    filename: str
    is_deepfake: Optional[bool] = None
    confidence: Optional[float] = None
    classification: Optional[str] = None
    risk_level: Optional[str] = None
    probabilities: Optional[Dict[str, float]] = None
    error: Optional[str] = None


class BatchSummary(BaseModel):
    deepfakes_detected: int
    real_images: int
    errors: int


class BatchResponse(BaseModel):
    total_files: int
    results: List[BatchResultItem]
    summary: BatchSummary


# ── Liveness Detection ─────────────────────────────────

class LivenessChecks(BaseModel):
    face_detected: bool
    texture_score: float
    frequency_score: float
    color_score: float
    edge_score: float
    sharpness_score: float


class LivenessImageResponse(BaseModel):
    is_live: bool
    liveness_score: float
    checks: LivenessChecks
    risk_level: str
    classification: str          # "LIVE" or "SPOOF"
    processing_time_ms: float


class LivenessVideoResponse(BaseModel):
    is_live: bool
    liveness_score: float
    frames_analyzed: int
    live_frames: int
    live_percentage: float
    risk_level: str
    classification: str
    frame_results: List[Dict]
    processing_time_ms: float


# ── Voice Detection ────────────────────────────────────

class VoiceResponse(BaseModel):
    is_synthetic: bool
    confidence: float
    human_score: float
    synthetic_score: float
    classification: str        # "HUMAN" or "SYNTHETIC"
    risk_level: str
    model_used: str            # "hf_api" or "local_spectral"
    processing_time_ms: float


# ── Behavior Detection ─────────────────────────────────

class KeystrokeItem(BaseModel):
    key: str
    timestamp_ms: float

class MouseMovementItem(BaseModel):
    x: float
    y: float
    timestamp_ms: float

class BehaviorRequest(BaseModel):
    keystrokes: List[KeystrokeItem] = []
    mouse_movements: List[MouseMovementItem] = []

class BehaviorChecks(BaseModel):
    typing_speed_score: float
    typing_rhythm_score: float
    mouse_speed_score: float
    mouse_straightness_score: float

class BehaviorResponse(BaseModel):
    is_human: bool
    behavior_score: float
    classification: str        # "HUMAN" or "BOT"
    risk_level: str
    checks: BehaviorChecks
    processing_time_ms: float


# ── KYC Verification ───────────────────────────────────

class KycDeepfakeCheck(BaseModel):
    is_deepfake: bool
    confidence: float
    classification: str
    risk_level: str


class KycLivenessCheck(BaseModel):
    is_live: bool
    liveness_score: float
    classification: str
    risk_level: str
    checks: LivenessChecks


class KycResponse(BaseModel):
    verdict: str                   # "PASS", "FAIL", or "REVIEW"
    reason: str
    overall_risk: str
    trust_score: Optional[float] = None
    explanation: Optional[List[str]] = None
    deepfake_check: KycDeepfakeCheck
    liveness_check: KycLivenessCheck
    processing_time_ms: float


# ── Session / Risk Engine ──────────────────────────────

class SessionCreateResponse(BaseModel):
    session_id: str
    created_at: str
    status: str

class AgentResult(BaseModel):
    score: float
    risk_level: str
    details: Optional[Dict] = None

class SessionResult(BaseModel):
    session_id: str
    trust_score: float
    decision: str              # "PASS", "REVIEW", or "FAIL"
    explanation: List[str]
    agents: Dict[str, AgentResult]
    overall_risk: str
    processing_time_ms: float


# ── Analytics ───────────────────────────────────────────

class AnalyticsSummary(BaseModel):
    total_verifications: int
    deepfakes_caught: int
    clean_results: int
    avg_confidence: float
    avg_processing_time_ms: float
    by_type: Dict[str, int]
    by_risk_level: Dict[str, int]


class RecentLogItem(BaseModel):
    id: int
    type: str
    filename: Optional[str]
    is_deepfake: Optional[bool]
    confidence: Optional[float]
    risk_level: Optional[str]
    processing_time_ms: Optional[float]
    created_at: Optional[str]


# ── Authentication ───────────────────────────────────────

class UserCreate(BaseModel):
    email: str
    password: str = Field(..., min_length=8)
    full_name: Optional[str] = None


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    full_name: Optional[str]
    is_active: bool
    created_at: datetime


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ── Verification History ─────────────────────────────────

class VerificationLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    verification_type: str
    filename: Optional[str]
    is_deepfake: Optional[bool]
    confidence: Optional[float]
    risk_level: Optional[str]
    processing_time_ms: Optional[float]
    created_at: datetime
