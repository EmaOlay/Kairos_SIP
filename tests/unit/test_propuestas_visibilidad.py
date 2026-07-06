"""
Tests del feature de visibilidad de propuestas (publicacion).

Cubren:
- GET /propuestas filtra por usuario autor.
- PATCH /propuestas/{id}/publicacion: toggle publicada, permisos de autor.
- GET /propuestas/publicadas: lista todas las publicadas (incluye propias).
- GET /propuestas/{id}: acceso basado en autor O publicada.
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


# Holder dinamico para cambiar el usuario "logueado" durante los tests
_current_user_holder = {"username": "alice", "rol": "decano"}


def _fake_user() -> UserOut:
    return UserOut(
        id=1,
        username=_current_user_holder["username"],
        nombre=f"User {_current_user_holder['username']}",
        rol=_current_user_holder["rol"],
    )


@pytest.fixture
def client_with_plan(plan_estudio_minimo, estudiante_basico):
    """
    TestClient con un plan + estudiante ya cargados en una SQLite in-memory
    compartida entre el override y el cliente.
    """
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
        from kairos.db.repository import EstudianteRepository
        EstudianteRepository(setup_session).upsert(estudiante_basico)

    def _override_get_db():
        db = TestingSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_current_user] = _fake_user
    yield TestClient(app), plan_estudio_minimo.codigo_plan
    app.dependency_overrides.clear()


class TestVisibilidadPropuestas:
    """Tests de acceso y visibilidad segun autor y estado de publicacion."""

    def test_get_propuestas_solo_devuelve_las_del_usuario(self, client_with_plan):
        """GET /propuestas autenticado como alice devuelve SOLO las de alice."""
        client, codigo = client_with_plan

        # Alice crea 2 propuestas
        _current_user_holder["username"] = "alice"
        client.post(f"/api/v1/planes/{codigo}/process", json={"config": None})
        client.post(f"/api/v1/planes/{codigo}/process", json={"config": None})

        # Bob crea 1 propuesta
        _current_user_holder["username"] = "bob"
        client.post(f"/api/v1/planes/{codigo}/process", json={"config": None})

        # Alice consulta: debe ver solo las 2 suyas
        _current_user_holder["username"] = "alice"
        r = client.get("/api/v1/propuestas")
        assert r.status_code == 200
        lista = r.json()
        assert len(lista) == 2
        assert all(item["usuario"] == "alice" for item in lista)

    def test_patch_publicacion_como_autor_devuelve_200(self, client_with_plan):
        """PATCH /propuestas/{id}/publicacion con publicada=true como autor -> 200."""
        client, codigo = client_with_plan

        _current_user_holder["username"] = "alice"
        post = client.post(f"/api/v1/planes/{codigo}/process", json={"config": None})
        propuesta_id = post.json()["propuesta_id"]

        # Publicar
        r = client.patch(
            f"/api/v1/propuestas/{propuesta_id}/publicacion",
            json={"publicada": True}
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["id"] == propuesta_id
        assert body["publicada"] is True

        # Verificar que persiste
        detalle = client.get(f"/api/v1/propuestas/{propuesta_id}").json()
        assert detalle.get("publicada") is True

    def test_patch_publicacion_toggle_funciona(self, client_with_plan):
        """Publicar y luego despublicar funciona (200 ambas)."""
        client, codigo = client_with_plan

        _current_user_holder["username"] = "alice"
        post = client.post(f"/api/v1/planes/{codigo}/process", json={"config": None})
        propuesta_id = post.json()["propuesta_id"]

        # Publicar
        r1 = client.patch(
            f"/api/v1/propuestas/{propuesta_id}/publicacion",
            json={"publicada": True}
        )
        assert r1.status_code == 200
        assert r1.json()["publicada"] is True

        # Despublicar
        r2 = client.patch(
            f"/api/v1/propuestas/{propuesta_id}/publicacion",
            json={"publicada": False}
        )
        assert r2.status_code == 200
        assert r2.json()["publicada"] is False

    def test_patch_publicacion_otro_usuario_devuelve_403(self, client_with_plan):
        """PATCH como otro usuario -> 403."""
        client, codigo = client_with_plan

        # Alice crea
        _current_user_holder["username"] = "alice"
        post = client.post(f"/api/v1/planes/{codigo}/process", json={"config": None})
        propuesta_id = post.json()["propuesta_id"]

        # Bob intenta publicar
        _current_user_holder["username"] = "bob"
        r = client.patch(
            f"/api/v1/propuestas/{propuesta_id}/publicacion",
            json={"publicada": True}
        )
        assert r.status_code == 403, r.text

    def test_patch_publicacion_id_inexistente_devuelve_404(self, client_with_plan):
        """PATCH con id inexistente -> 404."""
        client, _ = client_with_plan

        _current_user_holder["username"] = "alice"
        r = client.patch(
            "/api/v1/propuestas/9999/publicacion",
            json={"publicada": True}
        )
        assert r.status_code == 404

    def test_get_publicadas_devuelve_solo_las_publicadas(self, client_with_plan):
        """GET /propuestas/publicadas: con 3 propuestas (alice publicada, alice no publicada, bob publicada), alice ve 2."""
        client, codigo = client_with_plan

        # Alice: 1 publicada, 1 no publicada
        _current_user_holder["username"] = "alice"
        post_alice_pub = client.post(f"/api/v1/planes/{codigo}/process", json={"config": None})
        id_alice_pub = post_alice_pub.json()["propuesta_id"]
        client.patch(f"/api/v1/propuestas/{id_alice_pub}/publicacion", json={"publicada": True})

        client.post(f"/api/v1/planes/{codigo}/process", json={"config": None})  # no publicada

        # Bob: 1 publicada
        _current_user_holder["username"] = "bob"
        post_bob_pub = client.post(f"/api/v1/planes/{codigo}/process", json={"config": None})
        id_bob_pub = post_bob_pub.json()["propuesta_id"]
        client.patch(f"/api/v1/propuestas/{id_bob_pub}/publicacion", json={"publicada": True})

        # Alice consulta publicadas: debe ver 2 (la suya y la de bob)
        _current_user_holder["username"] = "alice"
        r = client.get("/api/v1/propuestas/publicadas")
        assert r.status_code == 200
        lista = r.json()
        assert len(lista) == 2
        ids = [item["id"] for item in lista]
        assert id_alice_pub in ids
        assert id_bob_pub in ids

    def test_get_publicadas_incluye_propias_publicadas(self, client_with_plan):
        """GET /propuestas/publicadas incluye las propias publicadas."""
        client, codigo = client_with_plan

        _current_user_holder["username"] = "alice"
        post = client.post(f"/api/v1/planes/{codigo}/process", json={"config": None})
        propuesta_id = post.json()["propuesta_id"]
        client.patch(f"/api/v1/propuestas/{propuesta_id}/publicacion", json={"publicada": True})

        r = client.get("/api/v1/propuestas/publicadas")
        assert r.status_code == 200
        lista = r.json()
        assert len(lista) >= 1
        assert any(item["id"] == propuesta_id and item["usuario"] == "alice" for item in lista)

    def test_get_propuesta_by_id_propia_no_publicada_devuelve_200(self, client_with_plan):
        """GET /propuestas/{id} propia no publicada como autor -> 200."""
        client, codigo = client_with_plan

        _current_user_holder["username"] = "alice"
        post = client.post(f"/api/v1/planes/{codigo}/process", json={"config": None})
        propuesta_id = post.json()["propuesta_id"]

        r = client.get(f"/api/v1/propuestas/{propuesta_id}")
        assert r.status_code == 200
        assert r.json()["usuario"] == "alice"

    def test_get_propuesta_by_id_ajena_no_publicada_devuelve_403(self, client_with_plan):
        """GET /propuestas/{id} ajena no publicada -> 403."""
        client, codigo = client_with_plan

        # Alice crea sin publicar
        _current_user_holder["username"] = "alice"
        post = client.post(f"/api/v1/planes/{codigo}/process", json={"config": None})
        propuesta_id = post.json()["propuesta_id"]

        # Bob intenta acceder
        _current_user_holder["username"] = "bob"
        r = client.get(f"/api/v1/propuestas/{propuesta_id}")
        assert r.status_code == 403

    def test_get_propuesta_by_id_ajena_publicada_devuelve_200(self, client_with_plan):
        """GET /propuestas/{id} ajena publicada -> 200."""
        client, codigo = client_with_plan

        # Alice crea y publica
        _current_user_holder["username"] = "alice"
        post = client.post(f"/api/v1/planes/{codigo}/process", json={"config": None})
        propuesta_id = post.json()["propuesta_id"]
        client.patch(f"/api/v1/propuestas/{propuesta_id}/publicacion", json={"publicada": True})

        # Bob accede
        _current_user_holder["username"] = "bob"
        r = client.get(f"/api/v1/propuestas/{propuesta_id}")
        assert r.status_code == 200
        assert r.json()["usuario"] == "alice"


class TestPermisosPorRol:
    """Tests del bloqueo por rol: docente_funcional es solo lectura."""

    def test_docente_funcional_no_puede_prender_motor(self, client_with_plan):
        """POST /planes/{codigo}/process con rol docente_funcional -> 403."""
        client, codigo = client_with_plan
        _current_user_holder["username"] = "carlos_docente"
        _current_user_holder["rol"] = "docente_funcional"
        try:
            r = client.post(f"/api/v1/planes/{codigo}/process", json={"config": None})
            assert r.status_code == 403
            assert "no puede generar" in r.json()["detail"].lower()
        finally:
            _current_user_holder["rol"] = "decano"

    def test_docente_funcional_no_puede_publicar(self, client_with_plan):
        """PATCH /propuestas/{id}/publicacion con rol docente_funcional -> 403."""
        client, codigo = client_with_plan

        # Alice (decano) crea una propuesta
        _current_user_holder["username"] = "alice"
        _current_user_holder["rol"] = "decano"
        post = client.post(f"/api/v1/planes/{codigo}/process", json={"config": None})
        propuesta_id = post.json()["propuesta_id"]

        # Carlos (docente) intenta publicarla (no es autor, pero el bloqueo
        # por rol pega ANTES que el check de autor)
        _current_user_holder["username"] = "carlos_docente"
        _current_user_holder["rol"] = "docente_funcional"
        try:
            r = client.patch(
                f"/api/v1/propuestas/{propuesta_id}/publicacion",
                json={"publicada": True},
            )
            assert r.status_code == 403
            assert "no puede publicar" in r.json()["detail"].lower()
        finally:
            _current_user_holder["rol"] = "decano"
