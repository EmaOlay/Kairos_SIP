"""aulas, docentes y historico de dictado

Incorpora al modelo las restricciones operativas de capacidad/cantidad de
aulas y disponibilidad horaria de docentes, mas el historico de cursos
dictados que sirve para estimar disponibilidad cuando no hay horario
fehaciente del docente.

Revision ID: 0002
Revises: 0001
Create Date: 2026-06-08

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "aulas",
        sa.Column("aula_id", sa.String(length=64), primary_key=True),
        sa.Column("nombre", sa.String(length=255), nullable=False),
        sa.Column("capacidad", sa.Integer(), nullable=False),
        sa.Column("sede", sa.String(length=255)),
        sa.Column("turnos_disponibles_json", sa.String(length=255)),
    )

    op.create_table(
        "docentes",
        sa.Column("docente_id", sa.String(length=64), primary_key=True),
        sa.Column("nombre", sa.String(length=255), nullable=False),
        sa.Column("materias_que_dicta_json", sa.String(length=2000)),
        sa.Column("disponibilidad_turnos_json", sa.String(length=255)),
        sa.Column("max_comisiones", sa.Integer(), server_default="3"),
        sa.Column(
            "horario_fehaciente",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
    )

    op.create_table(
        "historico_dictado",
        sa.Column("historico_id", sa.String(length=64), primary_key=True),
        sa.Column("docente_id", sa.String(length=64), nullable=False, index=True),
        sa.Column("docente_nombre", sa.String(length=255), nullable=False),
        sa.Column("codigo_materia", sa.String(length=64), nullable=False, index=True),
        sa.Column("nombre_materia", sa.String(length=255)),
        sa.Column("turno", sa.String(length=16), nullable=False),
        sa.Column("ano", sa.Integer(), nullable=False),
        sa.Column("cuatrimestre", sa.Integer(), nullable=False),
        sa.Column("cantidad_alumnos", sa.Integer()),
    )


def downgrade() -> None:
    op.drop_table("historico_dictado")
    op.drop_table("docentes")
    op.drop_table("aulas")
