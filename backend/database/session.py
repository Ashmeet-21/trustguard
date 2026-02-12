"""
TrustGuard - Database Session Management
Creates the engine and provides a get_db() dependency for FastAPI.
Falls back to SQLite if PostgreSQL is not available.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.utils import config


# Try PostgreSQL first, fall back to SQLite for local development
try:
    engine = create_engine(config.DATABASE_URL, pool_pre_ping=True)
    with engine.connect() as conn:
        pass  # Test connection
except Exception:
    # SQLite fallback — works without any DB server setup
    import os
    db_path = os.path.join(os.path.dirname(__file__), "..", "trustguard_dev.db")
    engine = create_engine(
        f"sqlite:///{db_path}",
        connect_args={"check_same_thread": False}
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    """
    FastAPI dependency — yields a DB session per request, closes after.

    Usage in route:
        @router.post("/something")
        async def something(db: Session = Depends(get_db)):
            db.query(...)
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
