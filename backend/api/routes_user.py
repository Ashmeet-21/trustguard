"""
TrustGuard - User Routes
Profile and verification history for authenticated users.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from jose import JWTError, jwt

from backend.api.schemas import UserResponse, VerificationLogResponse
from backend.database.session import get_db
from backend.database.models import User, VerificationLog
from backend.utils import config

router = APIRouter(prefix="/api/v1/user", tags=["User"])

# OAuth2 scheme — tells FastAPI to look for "Bearer <token>" header
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def _user_from_token(token: str, db: Session) -> Optional[User]:
    """Decode + verify a JWT and load its user. Returns None if the token is bad/expired or the user is gone/disabled."""
    try:
        payload = jwt.decode(token, config.JWT_SECRET_KEY, algorithms=[config.JWT_ALGORITHM], issuer="trustguard")
        user_id = int(payload["sub"])
    except (JWTError, KeyError, ValueError):
        return None

    user = db.query(User).filter(User.id == user_id).first()
    return user if user and user.is_active else None


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    """Extract and validate the current user from JWT token (401 if missing/invalid)."""
    user = _user_from_token(token, db)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


# Optional scheme — same as oauth2_scheme but doesn't auto-require the header
oauth2_scheme_optional = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


def get_optional_user(
    token: Optional[str] = Depends(oauth2_scheme_optional),
    db: Session = Depends(get_db),
) -> Optional[User]:
    """Like get_current_user but returns None instead of 401 when no token is present."""
    return _user_from_token(token, db) if token else None


@router.get("/me", response_model=UserResponse)
async def get_profile(current_user: User = Depends(get_current_user)):
    """Get the current user's profile."""
    return current_user


@router.get("/me/history", response_model=List[VerificationLogResponse])
async def get_verification_history(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
):
    """Get the current user's verification history."""
    logs = (
        db.query(VerificationLog)
        .filter(VerificationLog.user_id == current_user.id)
        .order_by(VerificationLog.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return logs
