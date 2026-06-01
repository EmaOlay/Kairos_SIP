"""
Capa de persistencia de Kairos (RF-008).

Expone session, base declarativa, modelos ORM y repositories
para que el motor pueda consumir datos desde una DB relacional.
"""

from kairos.db.session import SessionLocal, engine, get_db, get_database_url
from kairos.db.base import Base

__all__ = ["SessionLocal", "engine", "get_db", "get_database_url", "Base"]
