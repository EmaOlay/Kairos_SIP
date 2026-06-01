"""initial schema (RF-008)

Revision ID: 0001
Revises:
Create Date: 2026-06-01

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "planes",
        sa.Column("codigo_plan", sa.String(length=64), primary_key=True),
        sa.Column("nombre_carrera", sa.String(length=255), nullable=False),
        sa.Column("facultad", sa.String(length=255)),
        sa.Column("ano_vigencia", sa.Integer(), nullable=False),
        sa.Column("duracion_anos", sa.Integer(), nullable=False),
        sa.Column("total_creditos", sa.Integer()),
    )

    op.create_table(
        "materias",
        sa.Column("codigo", sa.String(length=64), primary_key=True),
        sa.Column(
            "plan_codigo",
            sa.String(length=64),
            sa.ForeignKey("planes.codigo_plan"),
            nullable=False,
            index=True,
        ),
        sa.Column("nombre", sa.String(length=255), nullable=False),
        sa.Column("ano", sa.Integer(), nullable=False),
        sa.Column("cuatrimestre", sa.Integer(), nullable=False),
        sa.Column("horas_teoricas", sa.Integer(), default=0),
        sa.Column("horas_practicas", sa.Integer(), default=0),
        sa.Column("creditos", sa.Integer()),
        sa.Column("descripcion", sa.String(length=1000)),
        sa.Column("turnos_disponibles_json", sa.String(length=255)),
        sa.Column("costo_por_turno_json", sa.String(length=500)),
    )

    op.create_table(
        "correlativas",
        sa.Column(
            "materia_codigo",
            sa.String(length=64),
            sa.ForeignKey("materias.codigo"),
            primary_key=True,
        ),
        sa.Column(
            "prerequisito_codigo",
            sa.String(length=64),
            sa.ForeignKey("materias.codigo"),
            primary_key=True,
        ),
    )

    op.create_table(
        "estudiantes",
        sa.Column("estudiante_id", sa.String(length=64), primary_key=True),
        sa.Column("codigo_carrera", sa.String(length=64), nullable=False),
        sa.Column("plan_estudio_id", sa.String(length=64), nullable=False, index=True),
        sa.Column("ano_ingreso", sa.Integer(), nullable=False),
        sa.Column("turno_preferido", sa.String(length=16), nullable=False, server_default="noche"),
    )

    op.create_table(
        "registros_trayectoria",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "estudiante_id",
            sa.String(length=64),
            sa.ForeignKey("estudiantes.estudiante_id"),
            nullable=False,
            index=True,
        ),
        sa.Column("codigo_materia", sa.String(length=64), nullable=False),
        sa.Column("nombre_materia", sa.String(length=255), nullable=False),
        sa.Column("estado", sa.String(length=32), nullable=False),
        sa.Column("ano_academico", sa.Integer(), nullable=False),
        sa.Column("cuatrimestre", sa.Integer(), nullable=False),
        sa.Column("calificacion", sa.Float()),
        sa.Column("fecha_aprobacion", sa.DateTime()),
    )

    op.create_table(
        "recursos",
        sa.Column("recurso_id", sa.String(length=64), primary_key=True),
        sa.Column("codigo_materia", sa.String(length=64), nullable=False, index=True),
        sa.Column("nombre_materia", sa.String(length=255), nullable=False),
        sa.Column("ano_academico", sa.Integer(), nullable=False),
        sa.Column("cuatrimestre", sa.Integer(), nullable=False),
        sa.Column("cupos_totales", sa.Integer(), nullable=False),
        sa.Column("cupos_ocupados", sa.Integer(), default=0),
        sa.Column("modalidad", sa.String(length=32), default="presencial"),
        sa.Column("horario_inicio", sa.String(length=5), nullable=False),
        sa.Column("horario_fin", sa.String(length=5), nullable=False),
        sa.Column("dias_semana", sa.String(length=255)),
        sa.Column("docente_id", sa.String(length=64)),
        sa.Column("docente_nombre", sa.String(length=255)),
        sa.Column("costo_operativo_base", sa.Float()),
        sa.Column("costo_por_alumno", sa.Float()),
    )


def downgrade() -> None:
    op.drop_table("recursos")
    op.drop_table("registros_trayectoria")
    op.drop_table("estudiantes")
    op.drop_table("correlativas")
    op.drop_table("materias")
    op.drop_table("planes")
