"""
Endpoints de autenticacion: login y datos del usuario actual.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from kairos.api.deps import get_db
from kairos.api.schemas.auth import LoginRequest, LoginResponse, UserOut
from kairos.core.auth import (
    authenticate_user,
    create_access_token,
    get_current_user,
)

router = APIRouter()


@router.post("/auth/login", response_model=LoginResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> LoginResponse:
    user = authenticate_user(db, payload.username, payload.password)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario o contrasena incorrectos",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = create_access_token(user)
    return LoginResponse(
        access_token=token,
        token_type="bearer",
        user=UserOut(id=user.id, username=user.username, nombre=user.nombre, rol=user.rol),
    )


@router.get("/auth/me", response_model=UserOut)
def me(current_user: UserOut = Depends(get_current_user)) -> UserOut:
    return current_user
