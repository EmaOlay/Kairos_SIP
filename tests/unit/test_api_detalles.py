"""
Tests de los endpoints de la tab Detalles (aulas, docentes, estudiantes).

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


class TestListarAulas:
    def test_db_vacia(self, client):
        """Con DB vacia devuelve 200 y lista vacia."""
        r = client.get("/api/v1/aulas")
        assert r.status_code == 200
        assert r.json() == []

    def test_con_datos_ingestados(self, client):
        """Con datos ingestados devuelve 200 y la lista."""
        payload = [
            {"aula_id": "A1", "nombre": "Aula 1", "capacidad": 40},
            {"aula_id": "A2", "nombre": "Aula 2", "capacidad": 30, "turnos_disponibles": ["noche"]},
        ]
        ingest_r = client.post("/api/v1/aulas", json=payload)
        assert ingest_r.status_code == 201

        r = client.get("/api/v1/aulas")
        assert r.status_code == 200
        data = r.json()
        assert len(data) == 2
        assert data[0]["aula_id"] == "A1"
        assert data[0]["capacidad"] == 40
        assert data[1]["turnos_disponibles"] == ["noche"]


class TestListarDocentes:
    def test_db_vacia(self, client):
        """Con DB vacia devuelve 200 y lista vacia."""
        r = client.get("/api/v1/docentes")
        assert r.status_code == 200
        assert r.json() == []

    def test_con_datos_ingestados(self, client):
        """Con datos ingestados devuelve 200 y la lista."""
        payload = [
            {
                "docente_id": "D1",
                "nombre": "Ing. Test",
                "materias_que_dicta": ["3.4.069"],
                "disponibilidad_turnos": ["noche"],
                "max_comisiones": 3,
                "horario_fehaciente": True,
            },
            {
                "docente_id": "D2",
                "nombre": "Dra. Sin Horario",
                "materias_que_dicta": [],
                "disponibilidad_turnos": [],
                "horario_fehaciente": False,
            },
        ]
        ingest_r = client.post("/api/v1/docentes", json=payload)
        assert ingest_r.status_code == 201

        r = client.get("/api/v1/docentes")
        assert r.status_code == 200
        data = r.json()
        assert len(data) == 2
        assert data[0]["docente_id"] == "D1"
        assert data[0]["materias_que_dicta"] == ["3.4.069"]
        assert data[1]["horario_fehaciente"] is False
