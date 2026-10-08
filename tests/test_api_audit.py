"""
Tests for audit report API endpoints.
"""

import uuid

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


def _make_report(session_id, user_id):
    routes_audit.reporter.generate_report(session_id, {
        "session_id": session_id, "trust_score": 85.0, "decision": "PASS",
        "overall_risk": "LOW", "explanation": [], "agents": {}, "processing_time_ms": 1.0,
    }, user_id=user_id)


def test_audit_report_creation_and_retrieval(client, auth_headers):
    """Owner should be able to generate and retrieve their audit report."""
    reporter = routes_audit.reporter
    user_id = client.get("/api/v1/user/me", headers=auth_headers).json()["id"]
    session_id = str(uuid.uuid4())
    session_result = {
        "session_id": session_id,
        "trust_score": 85.0,
        "decision": "PASS",
        "overall_risk": "LOW",
        "explanation": ["image_agent: PASSED (score 90/100, risk LOW)"],
        "agents": {
            "image_agent": {"score": 90, "risk_level": "LOW"},
        },
        "processing_time_ms": 150.0,
    }
    reporter.generate_report(session_id, session_result, user_id=user_id)

    response = client.get(f"/api/v1/audit/{session_id}", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["session_id"] == session_id
    assert data["decision"] == "PASS"
    assert data["trust_score"] == 85.0


def test_recent_reports_endpoint(client, auth_headers):
    """Should return list of recent reports."""
    response = client.get("/api/v1/audit/?limit=5", headers=auth_headers)
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_cannot_read_other_users_report(client, auth_headers):
    """A logged-in user must not see someone else's (or an anonymous) report."""
    other_session = str(uuid.uuid4())
    _make_report(other_session, user_id=999999)
    assert client.get(f"/api/v1/audit/{other_session}", headers=auth_headers).status_code == 404

    recent = client.get("/api/v1/audit/?limit=100", headers=auth_headers).json()
    assert all(r["session_id"] != other_session for r in recent)


def test_audit_rejects_non_uuid_session_id(client, auth_headers):
    """session_id goes into a file path — anything that isn't a UUID must be rejected (path traversal)."""
    response = client.get("/api/v1/audit/..%5C..%5Csecrets", headers=auth_headers)
    assert response.status_code == 404
