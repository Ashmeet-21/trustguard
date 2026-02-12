"""
TrustGuard - Database Models
Defines User, VerificationLog, and AuditLog tables.
"""

from sqlalchemy import Column, Integer, String, Boolean, Float, DateTime, ForeignKey, JSON
from sqlalchemy.orm import DeclarativeBase, relationship
from datetime import datetime


class Base(DeclarativeBase):
    """Base class for all models."""
    pass


class User(Base):
    """Registered user account."""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # One user -> many verification logs
    verification_logs = relationship("VerificationLog", back_populates="user")

    def __repr__(self):
        return f"<User(id={self.id}, email='{self.email}')>"


class VerificationLog(Base):
    """Record of each detection/verification request."""
    __tablename__ = "verification_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # null = anonymous
    verification_type = Column(String(50), nullable=False)  # "deepfake_image", "deepfake_video", "batch"
    filename = Column(String(255), nullable=True)
    result_json = Column(JSON, nullable=True)
    is_deepfake = Column(Boolean, nullable=True)
    confidence = Column(Float, nullable=True)
    risk_level = Column(String(20), nullable=True)
    processing_time_ms = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Many logs -> one user
    user = relationship("User", back_populates="verification_logs")

    def __repr__(self):
        return f"<VerificationLog(id={self.id}, type='{self.verification_type}')>"


class AuditLog(Base):
    """Security audit trail for login, registration, etc."""
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    action = Column(String(100), nullable=False)  # "login", "register", "detect"
    ip_address = Column(String(45), nullable=True)
    details = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<AuditLog(id={self.id}, action='{self.action}')>"
