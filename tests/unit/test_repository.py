"""
Tests del modulo de persistencia (RF-008).

Usan SQLite in-memory para no depender de Postgres en CI.
La capa ORM es agnostica al engine, asi que el roundtrip
valida la logica de mapeo Pydantic <-> ORM.
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from kairos.core.optimizer import KairosOptimizer
from kairos.db.base import Base
from kairos.db.repository import (
    EstudianteRepository,
    PlanRepository,
    RecursoRepository,
)


@pytest.fixture
def session():
    """Sesion fresca con SQLite in-memory por test."""
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
    s = SessionLocal()
    try:
        yield s
    finally:
        s.close()


class TestPlanRepository:
    def test_roundtrip_plan_minimo(self, session, plan_estudio_minimo):
        """Persistir y leer un plan recupera materias y correlativas."""
        repo = PlanRepository(session)
        repo.upsert(plan_estudio_minimo)

        leido = repo.get(plan_estudio_minimo.codigo_plan)

        assert leido is not None
        assert leido.codigo_plan == plan_estudio_minimo.codigo_plan
        assert leido.nombre_carrera == plan_estudio_minimo.nombre_carrera
        assert len(leido.materias) == 2
        assert "3.4.069" in leido.materias
        assert leido.materias["3.4.070"].correlativas_anteriores == ["3.4.069"]

    def test_persiste_turnos_y_costos_rf003(self, session, plan_estudio_minimo):
        """Los campos turnos_disponibles y costo_por_turno (RF-003) se persisten."""
        repo = PlanRepository(session)
        repo.upsert(plan_estudio_minimo)

        leido = repo.get(plan_estudio_minimo.codigo_plan)
        materia = leido.materias["3.4.069"]
        assert materia.turnos_disponibles == ["manana", "tarde", "noche"]
        assert materia.costo_por_turno == {"manana": 3000, "tarde": 4000, "noche": 6000}

    def test_upsert_es_idempotente(self, session, plan_estudio_minimo):
        """Llamar upsert dos veces no duplica datos."""
        repo = PlanRepository(session)
        repo.upsert(plan_estudio_minimo)
        repo.upsert(plan_estudio_minimo)

        leido = repo.get(plan_estudio_minimo.codigo_plan)
        assert leido is not None
        assert len(leido.materias) == 2

    def test_get_inexistente_devuelve_none(self, session):
        repo = PlanRepository(session)
        assert repo.get("no-existe") is None

    def test_motor_consume_plan_desde_db(self, session, plan_estudio_minimo):
        """
        El KairosOptimizer debe poder procesar un plan que viene de la DB
        igual que uno construido desde JSON.
        """
        repo = PlanRepository(session)
        repo.upsert(plan_estudio_minimo)
        plan_db = repo.get(plan_estudio_minimo.codigo_plan)

        optimizer = KairosOptimizer(plan_db)
        assert len(optimizer.grafo_correlativas.nodes) == 2
        assert optimizer.grafo_correlativas.has_edge("3.4.069", "3.4.070")
        assert optimizer.tiene_ciclos() is False


class TestEstudianteRepository:
    def test_roundtrip_estudiante_con_registros(
        self, session, plan_estudio_minimo, estudiante_basico
    ):
        PlanRepository(session).upsert(plan_estudio_minimo)
        repo = EstudianteRepository(session)
        repo.upsert(estudiante_basico)

        leido = repo.get(estudiante_basico.estudiante_id)
        assert leido is not None
        assert len(leido.registros_trayectoria) == 2
        aprobadas = leido.materias_aprobadas
        assert "3.4.069" in aprobadas

    def test_persiste_turno_preferido_rf003(
        self, session, plan_estudio_minimo, estudiante_basico
    ):
        PlanRepository(session).upsert(plan_estudio_minimo)
        EstudianteRepository(session).upsert(estudiante_basico)

        leido = EstudianteRepository(session).get(estudiante_basico.estudiante_id)
        assert leido.turno_preferido == "noche"

    def test_list_by_plan(self, session, plan_estudio_minimo, estudiante_basico):
        PlanRepository(session).upsert(plan_estudio_minimo)
        EstudianteRepository(session).upsert(estudiante_basico)

        listados = EstudianteRepository(session).list_by_plan("1621")
        assert len(listados) == 1
        assert listados[0].estudiante_id == estudiante_basico.estudiante_id


class TestRecursoRepository:
    def test_roundtrip_recurso(self, session, recurso_disponible_basico):
        repo = RecursoRepository(session)
        repo.upsert(recurso_disponible_basico)

        listados = repo.list_all()
        assert len(listados) == 1
        r = listados[0]
        assert r.recurso_id == "COM001"
        assert r.dias_semana == ["Lunes", "Miercoles"]
        assert r.cupos_disponibles == 20
