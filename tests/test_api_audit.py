"""
Tests for audit report API endpoints.
"""

import pytest
from backend.api import routes_audit
from backend.core.audit_reporter import AuditReporter


@pytest.fixture(autouse=True)
def setup_audit_reporter():
    """Ensure audit reporter is initialized for tests."""
    original = routes_audit.reporter
    routes_audit.reporter = AuditReporter()
    yield
    routes_audit.reporter = original


def test_audit_requires_auth(client):
    """Audit reports should reject requests without a token."""
    response = client.get("/api/v1/audit/?limit=5")
    assert response.status_code == 401


def test_audit_report_not_found(client, auth_headers):
    """Should return 404 for non-existent session."""
    response = client.get("/api/v1/audit/nonexistent-session-id", headers=auth_headers)
    assert response.status_code == 404


def test_audit_report_creation_and_retrieval(client, auth_headers):
    """Should be able to generate and retrieve an audit report."""
    reporter = routes_audit.reporter
    # Manually generate a report
    session_result = {
        "session_id": "test-session-123",
        "trust_score": 85.0,
        "decision": "PASS",
        "overall_risk": "LOW",
        "explanation": ["image_agent: PASSED (score 90/100, risk LOW)"],
        "agents": {
            "image_agent": {"score": 90, "risk_level": "LOW"},
        },
        "processing_time_ms": 150.0,
    }
    reporter.generate_report("test-session-123", session_result)

    response = client.get("/api/v1/audit/test-session-123", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["session_id"] == "test-session-123"
    assert data["decision"] == "PASS"
    assert data["trust_score"] == 85.0


def test_recent_reports_endpoint(client, auth_headers):
    """Should return list of recent reports."""
    response = client.get("/api/v1/audit/?limit=5", headers=auth_headers)
    assert response.status_code == 200
    assert isinstance(response.json(), list)
