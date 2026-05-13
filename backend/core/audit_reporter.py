"""
Audit Reporter — Generates structured audit artifacts for each verification session.

Every verification gets a full audit report saved as JSON. This provides:
- Complete audit trail for compliance
- Debugging information for failed verifications
- Historical record of model versions and decisions

Reports are saved to backend/audit_reports/{session_id}.json and also
logged to the AuditLog database table.

INTERVIEW TIP: "Every verification creates an audit report with the full decision
chain — which agents ran, what they scored, what quality gates passed, and the
final verdict. This is essential for compliance in fintech/KYC."
"""

import json
import os
from collections import OrderedDict
from datetime import datetime
from pathlib import Path
from loguru import logger

from backend.database.session import SessionLocal
from backend.database.models import AuditLog


AUDIT_DIR = Path(__file__).parent.parent / "audit_reports"


class AuditReporter:
    """Generates and stores audit reports for verification sessions."""

    MAX_CACHE_SIZE = 1000

    def __init__(self):
        AUDIT_DIR.mkdir(exist_ok=True)
        self._reports = OrderedDict()  # Bounded LRU cache
        logger.info("Audit reporter initialized (dir={})", AUDIT_DIR)

    def generate_report(self, session_id: str, session_result: dict, metadata: dict = None) -> dict:
        """
        Create a full audit report for a verification session.

        Args:
            session_id: The session's unique ID
            session_result: The result from SessionOrchestrator.run_session()
            metadata: Optional extra info (IP address, user agent, etc.)

        Returns:
            Complete audit report dict
        """
        report = {
            "report_id": session_id,
            "timestamp": datetime.utcnow().isoformat(),
            "session_id": session_id,
            "decision": session_result.get("decision", "UNKNOWN"),
            "trust_score": session_result.get("trust_score", 0),
            "overall_risk": session_result.get("overall_risk", "UNKNOWN"),
            "explanation": session_result.get("explanation", []),
            "agents": {},
            "quality_gates": session_result.get("quality_gates", []),
            "processing_time_ms": session_result.get("processing_time_ms", 0),
            "metadata": metadata or {},
        }

        # Add per-agent details
        for agent_name, agent_data in session_result.get("agents", {}).items():
            report["agents"][agent_name] = {
                "score": agent_data.get("score", 0),
                "risk_level": agent_data.get("risk_level", "UNKNOWN"),
            }

        # Save and store
        self.save_report(report, session_id)
        self._reports[session_id] = report
        # Evict oldest if cache is full
        while len(self._reports) > self.MAX_CACHE_SIZE:
            self._reports.popitem(last=False)

        logger.info("Audit report generated for session {}", session_id)
        return report

    def save_report(self, report: dict, session_id: str):
        """Save audit report to JSON file and database."""
        # Save to file
        file_path = AUDIT_DIR / f"{session_id}.json"
        try:
            with open(file_path, "w") as f:
                json.dump(report, f, indent=2, default=str)
        except Exception as e:
            logger.error("Failed to save audit report file: {}", e)

        # Save to database
        try:
            db = SessionLocal()
            log = AuditLog(
                action="verification_completed",
                details=report,
            )
            db.add(log)
            db.commit()
            db.close()
        except Exception as e:
            logger.error("Failed to save audit report to DB: {}", e)

    def get_report(self, session_id: str) -> dict:
        """Retrieve an audit report by session ID."""
        # Check in-memory cache first
        if session_id in self._reports:
            return self._reports[session_id]

        # Try loading from file
        file_path = AUDIT_DIR / f"{session_id}.json"
        if file_path.exists():
            try:
                with open(file_path, "r") as f:
                    report = json.load(f)
                self._reports[session_id] = report
                while len(self._reports) > self.MAX_CACHE_SIZE:
                    self._reports.popitem(last=False)
                return report
            except Exception as e:
                logger.error("Failed to read audit report: {}", e)

        return None

    def get_recent_reports(self, limit: int = 10) -> list:
        """Get recent audit reports from database."""
        try:
            db = SessionLocal()
            logs = (
                db.query(AuditLog)
                .filter(AuditLog.action == "verification_completed")
                .order_by(AuditLog.created_at.desc())
                .limit(limit)
                .all()
            )
            db.close()

            return [
                {
                    "id": log.id,
                    "session_id": log.details.get("session_id", "") if log.details else "",
                    "decision": log.details.get("decision", "") if log.details else "",
                    "trust_score": log.details.get("trust_score", 0) if log.details else 0,
                    "created_at": log.created_at.isoformat() if log.created_at else "",
                }
                for log in logs
            ]
        except Exception as e:
            logger.error("Failed to get recent audit reports: {}", e)
            return []
