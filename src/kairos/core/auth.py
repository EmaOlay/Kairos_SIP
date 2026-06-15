"""
Servicio de autenticacion: hashing de contrasenas (SHA256 + salt) y JWT.

Decision de diseno: usamos SHA256 con salt aleatorio por usuario en formato
"<salt_hex>:<sha256_hex>". No es bcrypt (mas debil contra fuerza bruta) pero
fue el trade-off pedido para esta primera iteracion.
"""

from __future__ import annotations

import hashlib
import logging
import os
import secrets
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from typing import Optional

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from kairos.api.deps import get_db
from kairos.api.schemas.auth import UserOut
from kairos.db.models import UsuarioORM

logger = logging.getLogger(__name__)


_DEV_FALLBACK_SECRET = "kairos-dev-secret-change-me"
JWT_ALGORITHM = "HS256"
TOKEN_EXPIRES_HOURS = 8


@lru_cache(maxsize=1)
def _get_jwt_secret() -> str:
    """Devuelve el JWT secret. Cachea el valor para que rotaciones en runtime
    no rompan tokens emitidos. En entornos != dev exigimos KAIROS_JWT_SECRET."""
    secret = os.getenv("KAIROS_JWT_SECRET")
    env = os.getenv("KAIROS_ENV", "development").lower()

    if not secret:
        if env not in ("development", "dev", "test", "testing"):
            raise RuntimeError(
                "KAIROS_JWT_SECRET no esta seteado y KAIROS_ENV no es de desarrollo. "
                "Configurar el secreto antes de bootear."
            )
        logger.warning(
            "KAIROS_JWT_SECRET no esta seteado: usando secreto de DEV. "
            "Setealo en produccion."
        )
        return _DEV_FALLBACK_SECRET
    return secret


# OAuth2PasswordBearer expone el header Authorization: Bearer <token>
# y maneja el 401 automatico cuando falta. tokenUrl es solo informativo
# para Swagger UI.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def hash_password(password: str) -> str:
    """Devuelve "<salt_hex>:<sha256_hex>" con salt nuevo aleatorio."""
    salt = secrets.token_hex(16)
    digest = hashlib.sha256(f"{salt}{password}".encode("utf-8")).hexdigest()
    return f"{salt}:{digest}"


def verify_password(password: str, password_hash: str) -> bool:
    """Verifica una contrasena contra un hash en formato salt:digest."""
    try:
        salt, expected = password_hash.split(":", 1)
    except ValueError:
        return False
    digest = hashlib.sha256(f"{salt}{password}".encode("utf-8")).hexdigest()
    # secrets.compare_digest es resistente a timing attacks
    return secrets.compare_digest(digest, expected)


def create_access_token(user: UsuarioORM) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user.id),
        "username": user.username,
        "rol": user.rol,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(hours=TOKEN_EXPIRES_HOURS)).timestamp()),
    }
    return jwt.encode(payload, _get_jwt_secret(), algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> dict:
    return jwt.decode(token, _get_jwt_secret(), algorithms=[JWT_ALGORITHM])


def authenticate_user(db: Session, username: str, password: str) -> Optional[UsuarioORM]:
    user = db.execute(
        select(UsuarioORM).where(UsuarioORM.username == username)
    ).scalar_one_or_none()
    if user is None:
        return None
    if not verify_password(password, user.password_hash):
        return None
    return user


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> UserOut:
    credentials_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Credenciales invalidas",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_access_token(token)
    except jwt.PyJWTError:
        raise credentials_exc

    user_id = payload.get("sub")
    if user_id is None:
        raise credentials_exc

    try:
        user_id_int = int(user_id)
    except (TypeError, ValueError):
        raise credentials_exc

    user = db.get(UsuarioORM, user_id_int)
    if user is None:
        raise credentials_exc

    return UserOut(id=user.id, username=user.username, nombre=user.nombre, rol=user.rol)


def require_role(*roles_permitidos: str):
    """Factory de dependency: solo deja pasar a usuarios con alguno de esos roles."""

    def _checker(user: UserOut = Depends(get_current_user)) -> UserOut:
        if user.rol not in roles_permitidos:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tenes permisos para esta accion",
            )
        return user

    return _checker
