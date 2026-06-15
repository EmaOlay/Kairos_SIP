"""
Tests de integracion para el sistema de autenticacion de Kairos.

Cubrimos:
    - Hashing y verificacion de contrasenas (salt + sha256).
    - Round-trip de JWT (encode -> decode), tokens invalidos y expirados.
    - Endpoints /auth/login y /auth/me (TestClient).
    - RBAC en /users: GET/POST solo para rol 'decano'.

Estrategia:
    - SQLite en memoria con StaticPool para que TestClient comparta el mismo
      schema entre conexiones (no dependemos de Postgres ni de Alembic).
    - Override de la dependency `get_db` con un sessionmaker bindeado al
      engine in-memory.
    - Cada test arranca con DB limpia (fixture function-scoped).
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import jwt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from kairos.api.deps import get_db
from kairos.api.main import app
from kairos.core.auth import (
    JWT_ALGORITHM,
    TOKEN_EXPIRES_HOURS,
    _get_jwt_secret,
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)
from kairos.db.base import Base
from kairos.db.models import UsuarioORM


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def test_db():
    """
    Engine SQLite in-memory + sessionmaker. Crea todas las tablas, yieldea
    una sesion por test y dropea al final.

    StaticPool es necesario para que la base in-memory persista entre
    conexiones del TestClient.
    """
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(
        bind=engine, autoflush=False, autocommit=False, future=True
    )
    session = TestingSessionLocal()
    try:
        # Adjuntamos el sessionmaker para que el override pueda crear
        # sesiones nuevas por request, igual que en produccion.
        session.info["sessionmaker"] = TestingSessionLocal
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


@pytest.fixture
def client(test_db):
    """TestClient con override de get_db apuntando al engine in-memory."""
    TestingSessionLocal = test_db.info["sessionmaker"]

    def _override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = _override_get_db
    try:
        with TestClient(app) as c:
            yield c
    finally:
        app.dependency_overrides.pop(get_db, None)


@pytest.fixture
def seeded_users(test_db: Session):
    """
    Inserta tres usuarios (uno por rol) usando hash_password real.

    Replica los usuarios del seed de la migracion 0003.
    """
    usuarios = [
        UsuarioORM(
            username="docente1",
            password_hash=hash_password("docente1"),
            nombre="Docente Uno",
            rol="docente_funcional",
        ),
        UsuarioORM(
            username="director1",
            password_hash=hash_password("director1"),
            nombre="Director Uno",
            rol="director_departamento",
        ),
        UsuarioORM(
            username="decano1",
            password_hash=hash_password("decano1"),
            nombre="Decano Uno",
            rol="decano",
        ),
    ]
    test_db.add_all(usuarios)
    test_db.commit()
    for u in usuarios:
        test_db.refresh(u)
    return {u.username: u for u in usuarios}


def auth_headers(client: TestClient, username: str, password: str) -> dict:
    """Hace login y devuelve el header Authorization listo para usar."""
    resp = client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": password},
    )
    assert resp.status_code == 200, f"Login fallo: {resp.status_code} {resp.text}"
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# Tests de hashing
# ---------------------------------------------------------------------------


class TestHashing:
    """Hash de contrasenas: formato salt:digest, salt random, verificacion."""

    def test_hash_password_genera_distinto_cada_vez(self):
        """Mismo password tiene que dar hashes distintos (salt random)."""
        h1 = hash_password("mismaclave")
        h2 = hash_password("mismaclave")
        assert h1 != h2
        # Pero ambos deben verificar contra la misma password
        assert verify_password("mismaclave", h1)
        assert verify_password("mismaclave", h2)

    def test_verify_password_acepta_correcta(self):
        """verify_password devuelve True con la password correcta."""
        h = hash_password("super-secreto-123")
        assert verify_password("super-secreto-123", h) is True

    def test_verify_password_rechaza_incorrecta(self):
        """verify_password devuelve False con una password distinta."""
        h = hash_password("clave-correcta")
        assert verify_password("clave-incorrecta", h) is False

    def test_verify_password_rechaza_hash_malformado(self):
        """Si el hash no tiene ':', no debe explotar y devuelve False."""
        assert verify_password("loquesea", "esto-no-es-un-hash-valido") is False
        assert verify_password("loquesea", "") is False


# ---------------------------------------------------------------------------
# Tests de JWT
# ---------------------------------------------------------------------------


class TestJWT:
    """Encoding/decoding de tokens JWT, expiracion y errores."""

    def test_create_y_decode_round_trip(self, test_db: Session):
        """Crear token con un user y decodificarlo devuelve los claims esperados."""
        user = UsuarioORM(
            id=42,
            username="pepito",
            password_hash=hash_password("xxx"),
            nombre="Jose Perez",
            rol="docente_funcional",
        )
        token = create_access_token(user)
        payload = decode_access_token(token)

        assert payload["sub"] == "42"
        assert payload["username"] == "pepito"
        assert payload["rol"] == "docente_funcional"
        assert "iat" in payload
        assert "exp" in payload
        # exp debe estar ~8 horas en el futuro
        delta = payload["exp"] - payload["iat"]
        assert delta == TOKEN_EXPIRES_HOURS * 3600

    def test_decode_token_invalido_lanza_jwt_error(self):
        """Un string que no es JWT valido tiene que reventar con PyJWTError."""
        with pytest.raises(jwt.PyJWTError):
            decode_access_token("esto.no.es.un.jwt")

    def test_decode_token_firmado_con_otro_secreto_es_rechazado(self):
        """Token firmado con otro secret -> InvalidSignatureError (subclase de PyJWTError)."""
        payload = {
            "sub": "1",
            "username": "x",
            "rol": "decano",
            "iat": int(datetime.now(timezone.utc).timestamp()),
            "exp": int((datetime.now(timezone.utc) + timedelta(hours=1)).timestamp()),
        }
        token_falopa = jwt.encode(payload, "otro-secreto-cualquiera", algorithm=JWT_ALGORITHM)
        with pytest.raises(jwt.PyJWTError):
            decode_access_token(token_falopa)

    def test_token_expirado_es_rechazado(self):
        """
        Armamos manualmente un token con exp en el pasado y validamos
        que decode_access_token lo rechace (ExpiredSignatureError).
        """
        past = datetime.now(timezone.utc) - timedelta(hours=1)
        payload = {
            "sub": "1",
            "username": "x",
            "rol": "decano",
            "iat": int((past - timedelta(hours=1)).timestamp()),
            "exp": int(past.timestamp()),  # vencido hace 1 hora
        }
        expired_token = jwt.encode(payload, _get_jwt_secret(), algorithm=JWT_ALGORITHM)
        with pytest.raises(jwt.ExpiredSignatureError):
            decode_access_token(expired_token)


# ---------------------------------------------------------------------------
# Tests del endpoint /auth/login
# ---------------------------------------------------------------------------


class TestLoginEndpoint:
    """POST /api/v1/auth/login"""

    def test_login_ok_devuelve_token_y_user(self, client: TestClient, seeded_users):
        """Login con credenciales validas devuelve 200 + token + user."""
        resp = client.post(
            "/api/v1/auth/login",
            json={"username": "decano1", "password": "decano1"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "access_token" in body
        assert body["token_type"] == "bearer"
        assert body["user"]["username"] == "decano1"
        assert body["user"]["rol"] == "decano"
        assert body["user"]["nombre"] == "Decano Uno"
        # El token tiene que ser decodificable
        payload = decode_access_token(body["access_token"])
        assert payload["username"] == "decano1"
        assert payload["rol"] == "decano"

    def test_login_password_incorrecta_devuelve_401(self, client: TestClient, seeded_users):
        resp = client.post(
            "/api/v1/auth/login",
            json={"username": "decano1", "password": "passwordmala"},
        )
        assert resp.status_code == 401
        assert resp.json()["detail"] == "Usuario o contrasena incorrectos"

    def test_login_usuario_inexistente_devuelve_401(self, client: TestClient, seeded_users):
        resp = client.post(
            "/api/v1/auth/login",
            json={"username": "fantasma", "password": "lo-que-sea"},
        )
        assert resp.status_code == 401
        assert resp.json()["detail"] == "Usuario o contrasena incorrectos"

    def test_login_body_invalido_devuelve_422(self, client: TestClient, seeded_users):
        """Sin password el body es invalido -> 422 de Pydantic."""
        resp = client.post(
            "/api/v1/auth/login",
            json={"username": "decano1"},
        )
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Tests del endpoint /auth/me
# ---------------------------------------------------------------------------


class TestMeEndpoint:
    """GET /api/v1/auth/me"""

    def test_me_con_token_valido_devuelve_user(self, client: TestClient, seeded_users):
        headers = auth_headers(client, "docente1", "docente1")
        resp = client.get("/api/v1/auth/me", headers=headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["username"] == "docente1"
        assert body["rol"] == "docente_funcional"
        assert body["nombre"] == "Docente Uno"
        assert isinstance(body["id"], int)

    def test_me_sin_token_devuelve_401(self, client: TestClient, seeded_users):
        resp = client.get("/api/v1/auth/me")
        assert resp.status_code == 401

    def test_me_con_token_basura_devuelve_401(self, client: TestClient, seeded_users):
        resp = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer esto-no-es-un-jwt-valido"},
        )
        assert resp.status_code == 401

    def test_me_con_token_expirado_devuelve_401(self, client: TestClient, seeded_users):
        """Token con exp pasada -> 401."""
        past = datetime.now(timezone.utc) - timedelta(hours=1)
        payload = {
            "sub": str(seeded_users["decano1"].id),
            "username": "decano1",
            "rol": "decano",
            "iat": int((past - timedelta(hours=1)).timestamp()),
            "exp": int(past.timestamp()),
        }
        expired = jwt.encode(payload, _get_jwt_secret(), algorithm=JWT_ALGORITHM)
        resp = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {expired}"},
        )
        assert resp.status_code == 401

    def test_me_con_token_de_usuario_borrado_devuelve_401(
        self, client: TestClient, seeded_users, test_db: Session
    ):
        """Token valido pero el user ya no existe en la DB -> 401."""
        headers = auth_headers(client, "docente1", "docente1")
        # Borramos el usuario despues de loguearse
        test_db.delete(seeded_users["docente1"])
        test_db.commit()

        resp = client.get("/api/v1/auth/me", headers=headers)
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Tests de RBAC en /users
# ---------------------------------------------------------------------------


class TestUsersRBAC:
    """GET/POST /api/v1/users: solo rol 'decano' tiene permiso."""

    # ---- GET /users ----

    def test_get_users_decano_devuelve_200(self, client: TestClient, seeded_users):
        headers = auth_headers(client, "decano1", "decano1")
        resp = client.get("/api/v1/users", headers=headers)
        assert resp.status_code == 200
        usernames = [u["username"] for u in resp.json()]
        assert set(usernames) == {"docente1", "director1", "decano1"}

    def test_get_users_docente_devuelve_403(self, client: TestClient, seeded_users):
        headers = auth_headers(client, "docente1", "docente1")
        resp = client.get("/api/v1/users", headers=headers)
        assert resp.status_code == 403

    def test_get_users_director_devuelve_403(self, client: TestClient, seeded_users):
        headers = auth_headers(client, "director1", "director1")
        resp = client.get("/api/v1/users", headers=headers)
        assert resp.status_code == 403

    def test_get_users_sin_token_devuelve_401(self, client: TestClient, seeded_users):
        resp = client.get("/api/v1/users")
        assert resp.status_code == 401

    # ---- POST /users ----

    def test_create_user_decano_devuelve_201(self, client: TestClient, seeded_users):
        headers = auth_headers(client, "decano1", "decano1")
        resp = client.post(
            "/api/v1/users",
            headers=headers,
            json={
                "username": "nuevo1",
                "password": "clave1234",
                "nombre": "Usuario Nuevo",
                "rol": "docente_funcional",
            },
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["username"] == "nuevo1"
        assert body["rol"] == "docente_funcional"
        assert body["nombre"] == "Usuario Nuevo"
        # No queremos ver el password_hash en la respuesta
        assert "password" not in body
        assert "password_hash" not in body

    def test_create_user_docente_devuelve_403(self, client: TestClient, seeded_users):
        headers = auth_headers(client, "docente1", "docente1")
        resp = client.post(
            "/api/v1/users",
            headers=headers,
            json={
                "username": "nuevo2",
                "password": "clave1234",
                "nombre": "X",
                "rol": "docente_funcional",
            },
        )
        assert resp.status_code == 403

    def test_create_user_director_devuelve_403(self, client: TestClient, seeded_users):
        headers = auth_headers(client, "director1", "director1")
        resp = client.post(
            "/api/v1/users",
            headers=headers,
            json={
                "username": "nuevo3",
                "password": "clave1234",
                "nombre": "X",
                "rol": "docente_funcional",
            },
        )
        assert resp.status_code == 403

    def test_create_user_sin_token_devuelve_401(self, client: TestClient, seeded_users):
        resp = client.post(
            "/api/v1/users",
            json={
                "username": "nuevo4",
                "password": "clave1234",
                "nombre": "X",
                "rol": "docente_funcional",
            },
        )
        assert resp.status_code == 401

    def test_create_user_username_duplicado_devuelve_409(
        self, client: TestClient, seeded_users
    ):
        """Crear un user con un username que ya existe -> 409."""
        headers = auth_headers(client, "decano1", "decano1")
        resp = client.post(
            "/api/v1/users",
            headers=headers,
            json={
                "username": "docente1",  # ya existe en el seed
                "password": "clave1234",
                "nombre": "Otro",
                "rol": "docente_funcional",
            },
        )
        assert resp.status_code == 409
        assert "ya existe" in resp.json()["detail"].lower()

    def test_create_user_rol_invalido_devuelve_422(self, client: TestClient, seeded_users):
        """Un rol fuera del Literal permitido -> 422 de Pydantic."""
        headers = auth_headers(client, "decano1", "decano1")
        resp = client.post(
            "/api/v1/users",
            headers=headers,
            json={
                "username": "nuevo5",
                "password": "clave1234",
                "nombre": "X",
                "rol": "rector_supremo",  # rol invalido
            },
        )
        assert resp.status_code == 422

    def test_create_user_password_se_hashea(
        self, client: TestClient, seeded_users, test_db: Session
    ):
        """
        La password no debe almacenarse en plano: el password_hash de la fila
        creada nunca debe contener la password textual y debe verificarse
        con verify_password.
        """
        headers = auth_headers(client, "decano1", "decano1")
        password_plana = "claveSuperSecreta-123"
        resp = client.post(
            "/api/v1/users",
            headers=headers,
            json={
                "username": "nuevo-hash",
                "password": password_plana,
                "nombre": "Hash Test",
                "rol": "docente_funcional",
            },
        )
        assert resp.status_code == 201

        # Buscamos al user en la DB y verificamos el hash
        from sqlalchemy import select

        row = test_db.execute(
            select(UsuarioORM).where(UsuarioORM.username == "nuevo-hash")
        ).scalar_one()
        assert row.password_hash != password_plana
        assert ":" in row.password_hash  # formato salt:digest
        assert password_plana not in row.password_hash
        assert verify_password(password_plana, row.password_hash) is True
