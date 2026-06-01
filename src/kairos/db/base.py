"""
Base declarativa de SQLAlchemy.

Importar Base desde aca para que Alembic detecte todos los modelos.
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base declarativa para todos los modelos ORM de Kairos."""
    pass
