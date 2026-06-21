"""propuestas_generadas: historial de corridas del motor

Persiste cada corrida del motor con la configuracion usada, el payload
completo de la propuesta y metadatos resumidos. El usuario queda como
placeholder ("anonimo") hasta que se mergee el feature de login.

Revision ID: 0003
Revises: 0002
Create Date: 2026-06-21

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "propuestas_generadas",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "creada_en",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
            index=True,
        ),
        sa.Column("usuario", sa.String(length=128), nullable=False, server_default="anonimo"),
        sa.Column("codigo_plan", sa.String(length=64), nullable=False, index=True),
        sa.Column("carrera", sa.String(length=255), nullable=False),
        sa.Column("comisiones_a_abrir", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("demanda_total", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("materias_con_demanda", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("config_json", sa.Text(), nullable=False),
        sa.Column("propuesta_json", sa.Text(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("propuestas_generadas")
