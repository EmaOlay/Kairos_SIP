"""
Esquemas de la API para autenticacion.
"""

from typing import Literal
from pydantic import BaseModel, Field


RolLiteral = Literal["docente_funcional", "director_departamento", "decano"]


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=64)
    password: str = Field(..., min_length=1, max_length=128)


class UserOut(BaseModel):
    id: int
    username: str
    nombre: str
    rol: RolLiteral


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class CreateUserRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=64)
    password: str = Field(..., min_length=4, max_length=128)
    nombre: str = Field(..., min_length=1, max_length=255)
    rol: RolLiteral
