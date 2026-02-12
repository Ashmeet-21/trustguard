"""
TrustGuard - Test Configuration
Sets up test database and FastAPI test client.
"""

import os
import sys
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Make sure backend is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from backend.database.models import Base
from backend.database.session import get_db
from backend.main import app


# In-memory SQLite for fast tests
TEST_ENGINE = create_engine("sqlite:///./test_trustguard.db", connect_args={"check_same_thread": False})
TestSession = sessionmaker(autocommit=False, autoflush=False, bind=TEST_ENGINE)


def override_get_db():
    """Override the real DB with test DB."""
    db = TestSession()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    """Create tables before all tests, drop after."""
    Base.metadata.create_all(bind=TEST_ENGINE)
    yield
    Base.metadata.drop_all(bind=TEST_ENGINE)
    TEST_ENGINE.dispose()
    try:
        if os.path.exists("./test_trustguard.db"):
            os.remove("./test_trustguard.db")
    except PermissionError:
        pass  # Windows may still hold the file


@pytest.fixture()
def db():
    """Provide a clean DB session for each test."""
    session = TestSession()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture()
def client():
    """FastAPI test client with test DB injected."""
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
