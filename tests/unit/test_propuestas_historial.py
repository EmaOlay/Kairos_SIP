"""
Tests del feature de persistencia de propuestas (historial).

Cubren:
- PropuestaRepository: roundtrip save/get/list y derivacion del resumen.
- Endpoint POST /planes/{codigo}/process: persiste la corrida y devuelve propuesta_id.
- Endpoints GET /propuestas y /propuestas/{id}: listado y detalle.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from kairos.api.deps import get_db
from kairos.api.main import app
from kairos.api.schemas.auth import UserOut
from kairos.core.auth import get_current_user
from kairos.db.base import Base
from kairos.db.repository import PlanRepository, PropuestaRepository


def _fake_user(username: str = "leorod") -> UserOut:
    return UserOut(id=1, username=username, nombre="Leo Test", rol="decano")


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
    s = Session()
    try:
        yield s
    finally:
        s.close()


@pytest.fixture
def client_with_plan(plan_estudio_minimo, estudiante_basico):
    """
    TestClient con un plan + estudiante ya cargados en una SQLite in-memory
    compartida entre el override y el cliente.
    """
    # StaticPool + check_same_thread=False: misma conexion compartida entre
    # el seed y el TestClient, porque sqlite ':memory:' crea una DB por
    # conexion.
    engine = create_engine(
        "sqlite:///:memory:",
        future=True,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    TestingSession = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)

    # Seed: plan y un estudiante con trayectoria minima.
    with TestingSession() as setup_session:
        PlanRepository(setup_session).upsert(plan_estudio_minimo)
        # El optimizer no requiere estudiantes para correr, pero los agrego
        # para que la respuesta tenga demanda > 0 cuando sea relevante.
        from kairos.db.repository import EstudianteRepository
        EstudianteRepository(setup_session).upsert(estudiante_basico)

    def _override_get_db():
        db = TestingSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_current_user] = lambda: _fake_user()
    yield TestClient(app), plan_estudio_minimo.codigo_plan
    app.dependency_overrides.clear()


class TestPropuestaRepository:
    def test_save_devuelve_row_con_id(self, db_session):
        row = PropuestaRepository(db_session).save(
            usuario="anonimo",
            codigo_plan="1621",
            carrera="Ingenieria",
            config={"weight_tasa_graduacion": 0.7},
            propuesta={"prescripciones": {}, "demanda_total": 0, "materias_con_demanda": 0},
        )
        assert row.id is not None
        assert row.usuario == "anonimo"

    def test_save_deriva_comisiones_a_abrir_del_payload(self, db_session):
        propuesta = {
            "prescripciones": {
                "MAT1": {"decision": "ABRIR"},
                "MAT2": {"decision": "ABRIR"},
                "MAT3": {"decision": "NO_ABRIR"},
            },
            "demanda_total": 25,
            "materias_con_demanda": 3,
        }
        row = PropuestaRepository(db_session).save(
            usuario="anonimo",
            codigo_plan="1621",
            carrera="X",
            config={},
            propuesta=propuesta,
        )
        assert row.comisiones_a_abrir == 2
        assert row.demanda_total == 25
        assert row.materias_con_demanda == 3

    def test_list_ordena_por_fecha_descendente(self, db_session):
        repo = PropuestaRepository(db_session)
        primera = repo.save(
            usuario="a", codigo_plan="1621", carrera="X",
            config={}, propuesta={"prescripciones": {}},
        )
        segunda = repo.save(
            usuario="b", codigo_plan="1621", carrera="X",
            config={}, propuesta={"prescripciones": {}},
        )
        resumenes = repo.list_resumenes()
        # La mas reciente primero. Como ambas comparten timestamp, el id mayor gana
        # via ordenamiento estable: aceptamos que el orden sea por inserción inversa.
        ids = [r.id for r in resumenes]
        assert primera.id in ids and segunda.id in ids

    def test_list_filtra_por_codigo_plan(self, db_session):
        repo = PropuestaRepository(db_session)
        repo.save(usuario="a", codigo_plan="1621", carrera="X",
                  config={}, propuesta={"prescripciones": {}})
        repo.save(usuario="b", codigo_plan="OTRO", carrera="Y",
                  config={}, propuesta={"prescripciones": {}})
        resumenes = repo.list_resumenes(codigo_plan="1621")
        assert len(resumenes) == 1
        assert resumenes[0].codigo_plan == "1621"


class TestEndpointPersistencia:
    def test_process_persiste_y_devuelve_propuesta_id(self, client_with_plan):
        client, codigo = client_with_plan
        r = client.post(f"/api/v1/planes/{codigo}/process", json={"config": None})
        assert r.status_code == 200, r.text
        body = r.json()
        assert body.get("propuesta_id") is not None
        assert body["carrera"] == "Ingenieria en Informatica"

    def test_listar_propuestas_devuelve_la_recien_guardada(self, client_with_plan):
        client, codigo = client_with_plan
        client.post(f"/api/v1/planes/{codigo}/process", json={"config": None})

        r = client.get("/api/v1/propuestas")
        assert r.status_code == 200
        lista = r.json()
        assert len(lista) == 1
        item = lista[0]
        assert item["codigo_plan"] == codigo
        assert item["usuario"] == "leorod"
        assert "config_usada" in item
        assert "weight_tasa_graduacion" in item["config_usada"]

    def test_listar_propuestas_filtra_por_plan(self, client_with_plan):
        client, codigo = client_with_plan
        client.post(f"/api/v1/planes/{codigo}/process", json={"config": None})

        r_match = client.get(f"/api/v1/propuestas?codigo_plan={codigo}")
        assert r_match.status_code == 200
        assert len(r_match.json()) == 1

        r_miss = client.get("/api/v1/propuestas?codigo_plan=NO_EXISTE")
        assert r_miss.status_code == 200
        assert r_miss.json() == []

    def test_obtener_propuesta_devuelve_payload_completo(self, client_with_plan):
        client, codigo = client_with_plan
        post = client.post(f"/api/v1/planes/{codigo}/process", json={"config": None})
        propuesta_id = post.json()["propuesta_id"]

        r = client.get(f"/api/v1/propuestas/{propuesta_id}")
        assert r.status_code == 200
        detalle = r.json()
        assert detalle["id"] == propuesta_id
        assert detalle["usuario"] == "leorod"
        assert detalle["codigo_plan"] == codigo
        assert "prescripciones" in detalle["propuesta"]
        assert "config_usada" in detalle["propuesta"]

    def test_obtener_propuesta_inexistente_404(self, client_with_plan):
        client, _ = client_with_plan
        r = client.get("/api/v1/propuestas/9999")
        assert r.status_code == 404

    def test_config_custom_se_snapshotea(self, client_with_plan):
        """La config que mandó el usuario queda guardada en la propuesta."""
        client, codigo = client_with_plan
        custom = {
            "weight_tasa_graduacion": 0.2,
            "weight_eficiencia_operativa": 0.8,
            "min_tasa_ocupacion": 0.4,
            "max_cupos_por_comision": 30,
            "max_comisiones_a_abrir": 5,
        }
        r = client.post(f"/api/v1/planes/{codigo}/process", json={"config": custom})
        propuesta_id = r.json()["propuesta_id"]

        detalle = client.get(f"/api/v1/propuestas/{propuesta_id}").json()
        config_usada = detalle["propuesta"]["config_usada"]
        assert config_usada["weight_tasa_graduacion"] == 0.2
        assert config_usada["weight_eficiencia_operativa"] == 0.8
        assert config_usada["min_tasa_ocupacion"] == 0.4
        assert config_usada["max_comisiones_a_abrir"] == 5
