"""
Tests de los endpoints de ingesta DB-driven (aulas y docentes).

Usan SQLite in-memory via override de get_db, asi no dependen de Postgres.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from kairos.api.deps import get_db
from kairos.api.main import app
from kairos.db.base import Base


@pytest.fixture
def client():
    """TestClient con get_db apuntando a una SQLite in-memory fresca."""
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    TestingSession = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)

    def _override_get_db():
        db = TestingSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = _override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()


class TestIngestaAulas:
    def test_ingesta_ok(self, client):
        payload = [
            {"aula_id": "A1", "nombre": "Aula 1", "capacidad": 40},
            {"aula_id": "A2", "nombre": "Aula 2", "capacidad": 30, "turnos_disponibles": ["noche"]},
        ]
        r = client.post("/api/v1/aulas", json=payload)
        assert r.status_code == 201
        body = r.json()
        assert body["persistidos"] == 2
        assert body["rechazados"] == 0

    def test_rechazo_individual(self, client):
        """Un aula con capacidad invalida se rechaza sin abortar el batch."""
        payload = [
            {"aula_id": "BAD", "nombre": "Mala", "capacidad": -5},
            {"aula_id": "OK", "nombre": "Buena", "capacidad": 25},
        ]
        r = client.post("/api/v1/aulas", json=payload)
        assert r.status_code == 201
        body = r.json()
        assert body["persistidos"] == 1
        assert body["rechazados"] == 1
        assert "BAD" in body["errores"][0]

    def test_idempotente(self, client):
        payload = [{"aula_id": "A1", "nombre": "Aula 1", "capacidad": 40}]
        client.post("/api/v1/aulas", json=payload)
        r = client.post("/api/v1/aulas", json=payload)
        assert r.status_code == 201
        assert r.json()["persistidos"] == 1


class TestIngestaDocentes:
    def test_ingesta_ok(self, client):
        payload = [
            {
                "docente_id": "D1",
                "nombre": "Ing. Test",
                "materias_que_dicta": ["3.4.069"],
                "disponibilidad_turnos": ["noche"],
                "max_comisiones": 3,
                "horario_fehaciente": True,
            }
        ]
        r = client.post("/api/v1/docentes", json=payload)
        assert r.status_code == 201
        assert r.json()["persistidos"] == 1

    def test_docente_sin_horario(self, client):
        """Docente con horario no fehaciente y listas vacias es valido."""
        payload = [
            {
                "docente_id": "D2",
                "nombre": "Dra. Sin Horario",
                "materias_que_dicta": [],
                "disponibilidad_turnos": [],
                "horario_fehaciente": False,
            }
        ]
        r = client.post("/api/v1/docentes", json=payload)
        assert r.status_code == 201
        assert r.json()["persistidos"] == 1
