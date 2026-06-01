"""
Sesion y engine de SQLAlchemy.

La URL se lee de la env var DATABASE_URL. Si no esta seteada,
usamos un default apuntando al servicio de docker-compose.
"""

import os
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker


DEFAULT_DATABASE_URL = "postgresql+psycopg://kairos:kairos@kairos-db:5432/kairos"


def get_database_url() -> str:
    """Devuelve la URL de la DB desde el env, con fallback al servicio de docker."""
    return os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL)


def _build_engine(url: str) -> Engine:
    # SQLite (tests) necesita check_same_thread=False
    connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
    return create_engine(url, future=True, connect_args=connect_args)


engine: Engine = _build_engine(get_database_url())

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def get_db() -> Generator[Session, None, None]:
    """Dependency injection para FastAPI: una sesion por request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
