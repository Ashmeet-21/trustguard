"""
TrustGuard - Analytics Routes

WHY: Any real API needs a way to see usage stats — how many scans were done,
     how many deepfakes caught, what's the average processing time, etc.
     This is pure database querying with SQLAlchemy. No ML, just SQL.

INTERVIEW TIP: "I built analytics endpoints so admins can monitor the system.
It queries the verification_logs table and aggregates counts, averages, and
breakdowns by type. Standard SQLAlchemy querying."
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func

from backend.api.routes_user import get_current_user
from backend.database.session import get_db
from backend.database.models import User, VerificationLog

router = APIRouter(prefix="/api/v1/analytics", tags=["Analytics"])


@router.get("/summary")
async def get_summary(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """
    Overall platform stats — total scans, deepfakes caught, average confidence, etc.

    This is just SQL COUNT/AVG/SUM queries wrapped in an endpoint.
    """
    total = db.query(func.count(VerificationLog.id)).scalar() or 0
    deepfakes_caught = db.query(func.count(VerificationLog.id)).filter(
        VerificationLog.is_deepfake == True
    ).scalar() or 0
    avg_confidence = db.query(func.avg(VerificationLog.confidence)).scalar()
    avg_processing = db.query(func.avg(VerificationLog.processing_time_ms)).scalar()

    # Count by verification type (deepfake_image, liveness_image, kyc, etc.)
    type_counts = (
        db.query(
            VerificationLog.verification_type,
            func.count(VerificationLog.id),
        )
        .group_by(VerificationLog.verification_type)
        .all()
    )

    # Count by risk level
    risk_counts = (
        db.query(
            VerificationLog.risk_level,
            func.count(VerificationLog.id),
        )
        .filter(VerificationLog.risk_level.isnot(None))
        .group_by(VerificationLog.risk_level)
        .all()
    )

    return {
        "total_verifications": total,
        "deepfakes_caught": deepfakes_caught,
        "clean_results": total - deepfakes_caught,
        "avg_confidence": round(float(avg_confidence), 4) if avg_confidence else 0.0,
        "avg_processing_time_ms": round(float(avg_processing), 2) if avg_processing else 0.0,
        "by_type": {vtype: count for vtype, count in type_counts},
        "by_risk_level": {level: count for level, count in risk_counts},
    }


@router.get("/recent")
async def get_recent(
    limit: int = Query(default=20, le=100, ge=1),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Most recent verification results — like an activity feed.

    Returns the last N verification logs, newest first.
    """
    logs = (
        db.query(VerificationLog)
        .order_by(VerificationLog.created_at.desc())
        .limit(limit)
        .all()
    )

    return [
        {
            "id": log.id,
            "type": log.verification_type,
            "filename": log.filename,
            "is_deepfake": log.is_deepfake,
            "confidence": log.confidence,
            "risk_level": log.risk_level,
            "processing_time_ms": log.processing_time_ms,
            "created_at": log.created_at.isoformat() if log.created_at else None,
        }
        for log in logs
    ]
