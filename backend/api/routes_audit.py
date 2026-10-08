"""
TrustGuard - Audit Report Routes
Retrieve audit reports for verification sessions.
"""

from fastapi import APIRouter, Depends, HTTPException, Query

from backend.api.routes_user import get_current_user
from backend.database.models import User

router = APIRouter(prefix="/api/v1/audit", tags=["Audit"])

# Global reporter — set by main.py during startup
reporter = None


@router.get("/{session_id}")
async def get_audit_report(session_id: str, current_user: User = Depends(get_current_user)):
    """Retrieve the audit report for a specific verification session."""
    if reporter is None:
        raise HTTPException(status_code=503, detail="Audit reporter not initialized")

    report = reporter.get_report(session_id)
    # Users can only read their own reports (404, not 403, so we don't confirm others exist)
    if report is None or report.get("user_id") != current_user.id:
        raise HTTPException(status_code=404, detail="Audit report not found")

    return report


@router.get("/")
async def get_recent_reports(limit: int = Query(default=10, ge=1, le=100), current_user: User = Depends(get_current_user)):
    """List the current user's recent audit reports."""
    if reporter is None:
        raise HTTPException(status_code=503, detail="Audit reporter not initialized")

    return reporter.get_recent_reports(user_id=current_user.id, limit=limit)
