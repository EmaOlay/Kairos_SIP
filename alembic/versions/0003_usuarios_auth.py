"""usuarios y auth

Crea la tabla de usuarios para login simple con rol fijo y siembra
3 cuentas de prueba (una por rol). Las contrasenas iniciales son iguales
al username (docente1, director1, decano1) y deberian rotarse en prod.

Revision ID: 0003
Revises: 0002
Create Date: 2026-06-15

"""
import hashlib
import secrets
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _hash_password(password: str) -> str:
    """Replica kairos.core.auth.hash_password para no acoplar la migracion al codigo de la app."""
    salt = secrets.token_hex(16)
    digest = hashlib.sha256(f"{salt}{password}".encode("utf-8")).hexdigest()
    return f"{salt}:{digest}"


def upgrade() -> None:
    op.create_table(
        "usuarios",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("username", sa.String(length=64), nullable=False, unique=True, index=True),
        sa.Column("password_hash", sa.String(length=160), nullable=False),
        sa.Column("nombre", sa.String(length=255), nullable=False),
        sa.Column("rol", sa.String(length=32), nullable=False),
        sa.CheckConstraint(
            "rol IN ('docente_funcional', 'director_departamento', 'decano')",
            name="ck_usuarios_rol_valido",
        ),
    )

    usuarios_table = sa.table(
        "usuarios",
        sa.column("username", sa.String),
        sa.column("password_hash", sa.String),
        sa.column("nombre", sa.String),
        sa.column("rol", sa.String),
    )

    op.bulk_insert(
        usuarios_table,
        [
            {
                "username": "docente1",
                "password_hash": _hash_password("docente1"),
                "nombre": "Docente Funcional Demo",
                "rol": "docente_funcional",
            },
            {
                "username": "director1",
                "password_hash": _hash_password("director1"),
                "nombre": "Director de Departamento Demo",
                "rol": "director_departamento",
            },
            {
                "username": "decano1",
                "password_hash": _hash_password("decano1"),
                "nombre": "Decano Demo",
                "rol": "decano",
            },
        ],
    )


def downgrade() -> None:
    op.drop_table("usuarios")
