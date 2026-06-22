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
from kairos.api.schemas.auth import UserOut
from kairos.core.auth import get_current_user
from kairos.db.base import Base


def _fake_decano() -> UserOut:
    """Stub de usuario autenticado con rol que pasa cualquier require_role."""
    return UserOut(id=1, username="decano-test", nombre="Decano Test", rol="decano")


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
    # Bypaseamos auth: require_role depende internamente de get_current_user,
    # asi que con overridear este alcanza para los tests de listado.
    app.dependency_overrides[get_current_user] = _fake_decano
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
        a1 = next(a for a in data if a["aula_id"] == "A1")
        a2 = next(a for a in data if a["aula_id"] == "A2")
        assert a1["capacidad"] == 40
        assert a2["turnos_disponibles"] == ["noche"]


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
        d1 = next(d for d in data if d["docente_id"] == "D1")
        d2 = next(d for d in data if d["docente_id"] == "D2")
        assert d1["materias_que_dicta"] == ["3.4.069"]
        assert d2["horario_fehaciente"] is False
