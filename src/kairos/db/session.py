"""
Sesion y engine de SQLAlchemy.

La URL se lee de la env var DATABASE_URL (configurable via .env).
Si no esta seteada se cae al default de dev (servicio de docker-compose).
En produccion DATABASE_URL siempre tiene que venir del entorno.
"""

import os
from typing import Generator

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

# Cargar variables de entorno del archivo .env
load_dotenv()


# Fallback solo para desarrollo local. En prod siempre seteamos DATABASE_URL.
_DEV_FALLBACK_URL = "postgresql+psycopg://kairos:kairos@kairos-db:5432/kairos"


def get_database_url() -> str:
    """Devuelve la URL de la DB desde el env, con fallback al servicio de docker."""
    return os.getenv("DATABASE_URL", _DEV_FALLBACK_URL)


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
