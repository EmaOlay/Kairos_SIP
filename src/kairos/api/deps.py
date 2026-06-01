"""
Dependencies de FastAPI compartidas.
"""

from typing import Generator

from sqlalchemy.orm import Session

from kairos.db.session import SessionLocal


def get_db() -> Generator[Session, None, None]:
    """Yield una sesion SQLAlchemy y la cierra al terminar el request."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
