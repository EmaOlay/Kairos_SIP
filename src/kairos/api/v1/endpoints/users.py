"""
Endpoints de gestion de usuarios. Solo el rol 'decano' puede listar y crear.
"""

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from kairos.api.deps import get_db
from kairos.api.schemas.auth import CreateUserRequest, UserOut
from kairos.core.auth import hash_password, require_role
from kairos.db.models import UsuarioORM

router = APIRouter()


@router.get("/users", response_model=List[UserOut])
def list_users(
    db: Session = Depends(get_db),
    _: UserOut = Depends(require_role("decano")),
) -> List[UserOut]:
    rows = db.execute(select(UsuarioORM).order_by(UsuarioORM.id)).scalars().all()
    return [UserOut(id=u.id, username=u.username, nombre=u.nombre, rol=u.rol) for u in rows]


@router.post("/users", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def create_user(
    payload: CreateUserRequest,
    db: Session = Depends(get_db),
    _: UserOut = Depends(require_role("decano")),
) -> UserOut:
    user = UsuarioORM(
        username=payload.username,
        password_hash=hash_password(payload.password),
        nombre=payload.nombre,
        rol=payload.rol,
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe un usuario con ese username",
        )
    db.refresh(user)
    return UserOut(id=user.id, username=user.username, nombre=user.nombre, rol=user.rol)
