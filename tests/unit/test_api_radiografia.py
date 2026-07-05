"""
Tests HTTP del endpoint GET /api/v1/estudiantes/{legajo}/radiografia.

Usa SQLite in-memory via override de get_db (mismo patron que test_repository):
al importar los repositories se registran los modelos en Base.metadata antes
del create_all, asi las tablas existen.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from kairos.api.deps import get_db
from kairos.api.main import app
from kairos.db.base import Base
from kairos.db.repository import EstudianteRepository, PlanRepository
from kairos.schemas.data_models import (
    EstadoMateria,
    EstudianteTrayectoria,
    Materia,
    PlanEstudio,
    RegistroTrayectoria,
)


def _materia(codigo, ano, cuatri, prereqs=None):
    return Materia(
        codigo=codigo,
        nombre=f"Materia {codigo}",
        ano=ano,
        cuatrimestre=cuatri,
        correlativas_anteriores=prereqs or [],
    )


@pytest.fixture
def session_factory():
    """
    Engine SQLite in-memory compartido entre el test y el override.

    StaticPool + check_same_thread=False mantienen una unica conexion in-memory:
    sin esto cada conexion del pool (y el hilo del TestClient) abriria su propia
    DB vacia y las tablas sembradas "desaparecerian" (no such table).
    """
    engine = create_engine(
        "sqlite:///:memory:",
        future=True,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


@pytest.fixture
def client(session_factory):
    """TestClient con get_db apuntando a la SQLite in-memory sembrada."""

    def _override_get_db():
        db = session_factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = _override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def seed(session_factory):
    """Siembra un plan en cadena A->B->C->D y un alumno con A aprobada, B regular."""
    db = session_factory()
    plan = PlanEstudio(
        codigo_plan="1621",
        nombre_carrera="Ingenieria en Informatica",
        ano_vigencia=2021,
        duracion_anos=5,
        materias={
            "A": _materia("A", 1, 1),
            "B": _materia("B", 1, 2, ["A"]),
            "C": _materia("C", 2, 1, ["B"]),
            "D": _materia("D", 2, 2, ["C"]),
        },
    )
    PlanRepository(db).upsert(plan)
    estudiante = EstudianteTrayectoria(
        estudiante_id="EST0007",
        codigo_carrera="ING_INF",
        plan_estudio_id="1621",
        ano_ingreso=2023,
        registros_trayectoria=[
            RegistroTrayectoria(
                codigo_materia="A", nombre_materia="Materia A",
                estado=EstadoMateria.APROBADA, ano_academico=2023, cuatrimestre=1,
            ),
            RegistroTrayectoria(
                codigo_materia="B", nombre_materia="Materia B",
                estado=EstadoMateria.REGULAR, ano_academico=2024, cuatrimestre=1,
            ),
        ],
    )
    EstudianteRepository(db).upsert(estudiante)
    db.close()


class TestRadiografiaEndpoint:
    def test_happy_path(self, client, seed):
        """Devuelve 200 y clasifica el plan del alumno en los cuatro grupos."""
        resp = client.get("/api/v1/estudiantes/EST0007/radiografia")
        assert resp.status_code == 200

        data = resp.json()
        assert data["estudiante_id"] == "EST0007"
        assert data["plan"] == "1621"
        assert data["resumen"]["total_materias"] == 4
        assert data["resumen"]["porcentaje_avance"] == 25.0
        assert [m["codigo"] for m in data["aprobadas"]] == ["A"]
        assert [m["codigo"] for m in data["pendientes_de_final"]] == ["B"]
        assert [m["codigo"] for m in data["disponibles_a_cursar"]] == ["C"]
        assert [m["codigo"] for m in data["bloqueadas"]] == ["D"]

    def test_final_condicionado_en_respuesta(self, client, seed):
        """C aparece cursable pero con el final condicionado a aprobar B."""
        resp = client.get("/api/v1/estudiantes/EST0007/radiografia")
        c = next(m for m in resp.json()["disponibles_a_cursar"] if m["codigo"] == "C")
        assert c["final_condicionado"] is True
        assert c["correlativas_a_aprobar_para_final"] == ["B"]

    def test_alumno_inexistente_da_404(self, client, seed):
        """Legajo que no existe -> 404 con mensaje claro."""
        resp = client.get("/api/v1/estudiantes/NOEXISTE/radiografia")
        assert resp.status_code == 404
        assert "NOEXISTE" in resp.json()["detail"]

    def test_alumno_con_plan_ausente_da_404(self, client, session_factory):
        """Alumno cuyo plan no esta cargado -> 404 (no revienta el motor)."""
        db = session_factory()
        EstudianteRepository(db).upsert(
            EstudianteTrayectoria(
                estudiante_id="EST0099",
                codigo_carrera="ING_INF",
                plan_estudio_id="9999",
                ano_ingreso=2023,
                registros_trayectoria=[],
            )
        )
        db.close()

        resp = client.get("/api/v1/estudiantes/EST0099/radiografia")
        assert resp.status_code == 404
