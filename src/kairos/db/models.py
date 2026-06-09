"""
Modelos ORM (SQLAlchemy 2.0) para la persistencia de Kairos.

Mapean uno a uno con los modelos Pydantic de kairos.schemas.data_models.
Las correlativas se modelan como una tabla relacional pura para
mantener compatibilidad con SQL Server / PostgreSQL / MySQL.

turnos_disponibles y costo_por_turno (RF-003) se serializan como JSON
en una columna String para mantener portabilidad entre engines.
"""

from datetime import datetime
from typing import List, Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from kairos.db.base import Base


class PlanORM(Base):
    __tablename__ = "planes"

    codigo_plan: Mapped[str] = mapped_column(String(64), primary_key=True)
    nombre_carrera: Mapped[str] = mapped_column(String(255), nullable=False)
    facultad: Mapped[Optional[str]] = mapped_column(String(255))
    ano_vigencia: Mapped[int] = mapped_column(Integer, nullable=False)
    duracion_anos: Mapped[int] = mapped_column(Integer, nullable=False)
    total_creditos: Mapped[Optional[int]] = mapped_column(Integer)

    materias: Mapped[List["MateriaORM"]] = relationship(
        back_populates="plan",
        cascade="all, delete-orphan",
    )


class MateriaORM(Base):
    __tablename__ = "materias"

    codigo: Mapped[str] = mapped_column(String(64), primary_key=True)
    plan_codigo: Mapped[str] = mapped_column(
        String(64), ForeignKey("planes.codigo_plan"), nullable=False, index=True
    )
    nombre: Mapped[str] = mapped_column(String(255), nullable=False)
    ano: Mapped[int] = mapped_column(Integer, nullable=False)
    cuatrimestre: Mapped[int] = mapped_column(Integer, nullable=False)
    horas_teoricas: Mapped[Optional[int]] = mapped_column(Integer, default=0)
    horas_practicas: Mapped[Optional[int]] = mapped_column(Integer, default=0)
    creditos: Mapped[Optional[int]] = mapped_column(Integer)
    descripcion: Mapped[Optional[str]] = mapped_column(String(1000))

    # RF-003: serializados como JSON-string para portabilidad cross-engine
    turnos_disponibles_json: Mapped[Optional[str]] = mapped_column(String(255))
    costo_por_turno_json: Mapped[Optional[str]] = mapped_column(String(500))

    plan: Mapped[PlanORM] = relationship(back_populates="materias")

    correlativas_anteriores: Mapped[List["CorrelativaORM"]] = relationship(
        back_populates="materia",
        foreign_keys="CorrelativaORM.materia_codigo",
        cascade="all, delete-orphan",
    )


class CorrelativaORM(Base):
    """
    Tabla puente: materia_codigo requiere prerequisito_codigo aprobada.
    """
    __tablename__ = "correlativas"

    materia_codigo: Mapped[str] = mapped_column(
        String(64), ForeignKey("materias.codigo"), primary_key=True
    )
    prerequisito_codigo: Mapped[str] = mapped_column(
        String(64), ForeignKey("materias.codigo"), primary_key=True
    )

    materia: Mapped[MateriaORM] = relationship(
        back_populates="correlativas_anteriores",
        foreign_keys=[materia_codigo],
    )


class EstudianteORM(Base):
    __tablename__ = "estudiantes"

    estudiante_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    codigo_carrera: Mapped[str] = mapped_column(String(64), nullable=False)
    plan_estudio_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    ano_ingreso: Mapped[int] = mapped_column(Integer, nullable=False)
    turno_preferido: Mapped[str] = mapped_column(String(16), default="noche")  # RF-003

    registros: Mapped[List["RegistroTrayectoriaORM"]] = relationship(
        back_populates="estudiante",
        cascade="all, delete-orphan",
    )


class RegistroTrayectoriaORM(Base):
    __tablename__ = "registros_trayectoria"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    estudiante_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("estudiantes.estudiante_id"), nullable=False, index=True
    )
    codigo_materia: Mapped[str] = mapped_column(String(64), nullable=False)
    nombre_materia: Mapped[str] = mapped_column(String(255), nullable=False)
    estado: Mapped[str] = mapped_column(String(32), nullable=False)
    ano_academico: Mapped[int] = mapped_column(Integer, nullable=False)
    cuatrimestre: Mapped[int] = mapped_column(Integer, nullable=False)
    calificacion: Mapped[Optional[float]] = mapped_column(Float)
    fecha_aprobacion: Mapped[Optional[datetime]] = mapped_column(DateTime)

    estudiante: Mapped[EstudianteORM] = relationship(back_populates="registros")


class RecursoORM(Base):
    __tablename__ = "recursos"

    recurso_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    codigo_materia: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    nombre_materia: Mapped[str] = mapped_column(String(255), nullable=False)
    ano_academico: Mapped[int] = mapped_column(Integer, nullable=False)
    cuatrimestre: Mapped[int] = mapped_column(Integer, nullable=False)

    cupos_totales: Mapped[int] = mapped_column(Integer, nullable=False)
    cupos_ocupados: Mapped[int] = mapped_column(Integer, default=0)

    modalidad: Mapped[str] = mapped_column(String(32), default="presencial")
    horario_inicio: Mapped[str] = mapped_column(String(5), nullable=False)
    horario_fin: Mapped[str] = mapped_column(String(5), nullable=False)
    dias_semana: Mapped[Optional[str]] = mapped_column(String(255))

    docente_id: Mapped[Optional[str]] = mapped_column(String(64))
    docente_nombre: Mapped[Optional[str]] = mapped_column(String(255))

    costo_operativo_base: Mapped[Optional[float]] = mapped_column(Float)
    costo_por_alumno: Mapped[Optional[float]] = mapped_column(Float)


class AulaORM(Base):
    """Aula fisica con su capacidad. Restriccion dura del motor."""

    __tablename__ = "aulas"

    aula_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    nombre: Mapped[str] = mapped_column(String(255), nullable=False)
    capacidad: Mapped[int] = mapped_column(Integer, nullable=False)
    sede: Mapped[Optional[str]] = mapped_column(String(255))
    # turnos_disponibles serializado como JSON-string (portabilidad cross-engine)
    turnos_disponibles_json: Mapped[Optional[str]] = mapped_column(String(255))


class DocenteORM(Base):
    """Docente del pool: materias que dicta + disponibilidad horaria."""

    __tablename__ = "docentes"

    docente_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    nombre: Mapped[str] = mapped_column(String(255), nullable=False)
    # Listas serializadas como JSON-string para portabilidad cross-engine
    materias_que_dicta_json: Mapped[Optional[str]] = mapped_column(String(2000))
    disponibilidad_turnos_json: Mapped[Optional[str]] = mapped_column(String(255))
    max_comisiones: Mapped[int] = mapped_column(Integer, default=3)
    horario_fehaciente: Mapped[bool] = mapped_column(Boolean, default=True)


class HistoricoDictadoORM(Base):
    """Curso historico dictado por un docente (insumo de estimacion)."""

    __tablename__ = "historico_dictado"

    historico_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    docente_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    docente_nombre: Mapped[str] = mapped_column(String(255), nullable=False)
    codigo_materia: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    nombre_materia: Mapped[Optional[str]] = mapped_column(String(255))
    turno: Mapped[str] = mapped_column(String(16), nullable=False)
    ano: Mapped[int] = mapped_column(Integer, nullable=False)
    cuatrimestre: Mapped[int] = mapped_column(Integer, nullable=False)
    cantidad_alumnos: Mapped[Optional[int]] = mapped_column(Integer)
