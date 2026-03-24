"""
Database connection and session management.
Handles lazy initialization for Railway deployments where
the DATABASE_URL may be injected after the container starts.
"""

import logging
import time
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from contextlib import contextmanager

from models import Base

logger = logging.getLogger(__name__)

engine = None
SessionLocal = None


def _get_db_url() -> str:
    """Get and normalize the database URL at runtime."""
    import os
    db_url = os.getenv("DATABASE_URL", "")
    if not db_url:
        raise RuntimeError(
            "DATABASE_URL environment variable is not set. "
            "Add a PostgreSQL database to your Railway project."
        )
    # Railway may use postgres:// instead of postgresql://
    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)
    return db_url


def _init_engine():
    """Create the SQLAlchemy engine (lazy, called once)."""
    global engine, SessionLocal

    db_url = _get_db_url()

    engine = create_engine(
        db_url,
        pool_size=10,
        max_overflow=20,
        pool_pre_ping=True,
    )
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    logger.info("Database engine created successfully.")


def _ensure_engine():
    """Ensure the engine is initialized."""
    if engine is None:
        _init_engine()


def init_db(retries: int = 5, delay: float = 2.0):
    """Create all tables. Retries on connection failure for Railway cold starts."""
    _ensure_engine()

    for attempt in range(1, retries + 1):
        try:
            # Test connection first
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            # Create tables
            Base.metadata.create_all(bind=engine)
            logger.info("Database tables created/verified successfully.")
            return
        except Exception as e:
            logger.warning(f"DB init attempt {attempt}/{retries} failed: {e}")
            if attempt < retries:
                time.sleep(delay)
            else:
                raise RuntimeError(
                    f"Could not connect to database after {retries} attempts: {e}"
                )


def get_db():
    """FastAPI dependency for database sessions."""
    _ensure_engine()
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def get_db_context():
    """Context manager for use outside of FastAPI routes."""
    _ensure_engine()
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
