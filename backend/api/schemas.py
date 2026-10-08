"""
TrustGuard - API Request/Response Schemas
Pydantic models for input validation and output serialization.
"""

from pydantic import BaseModel, ConfigDict, Field, field_validator
from typing import Optional, List
from datetime import datetime
import re


# ── Behavior Detection ─────────────────────────────────

class KeystrokeItem(BaseModel):
    key: str = Field(..., max_length=20)
    timestamp_ms: float

class MouseMovementItem(BaseModel):
    x: float
    y: float
    timestamp_ms: float

class BehaviorRequest(BaseModel):
    # Caps stop someone sending millions of points to tie up the server
    keystrokes: List[KeystrokeItem] = Field(default=[], max_length=2000)
    mouse_movements: List[MouseMovementItem] = Field(default=[], max_length=5000)


# ── Authentication ───────────────────────────────────────

class UserCreate(BaseModel):
    email: str = Field(..., max_length=255)
    password: str = Field(..., min_length=1, max_length=72)  # bcrypt only uses the first 72 bytes
    full_name: Optional[str] = Field(None, max_length=255)

    @field_validator("email")
    @classmethod
    def validate_email_format(cls, v: str) -> str:
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(pattern, v):
            raise ValueError("Invalid email format")
        return v.lower().strip()

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 12:
            raise ValueError("Password must be at least 12 characters")
        if not re.search(r'[A-Z]', v):
            raise ValueError("Password must contain an uppercase letter")
        if not re.search(r'[a-z]', v):
            raise ValueError("Password must contain a lowercase letter")
        if not re.search(r'[0-9]', v):
            raise ValueError("Password must contain a digit")
        if not re.search(r'[^A-Za-z0-9]', v):
            raise ValueError("Password must contain a special character")
        return v


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
