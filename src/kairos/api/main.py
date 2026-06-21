"""
Punto de entrada de la API REST de Kairos

Aca configuramos el boliche: FastAPI, los routers y los middlewares.
Es el cerebro que comunica el motor con el mundo exterior.
"""

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from kairos.api.v1.endpoints import auth, db_planes, optimizer, users

app = FastAPI(
    title="Kairos API",
    description="Motor de Analitica Prescriptiva para Optimizacion Academica",
    version="0.1.0",
)

# CORS: el front puede vivir en distintos puertos segun como se levante.
# allow_credentials=True con origins=["*"] es invalido segun spec, asi que
# listamos los orígenes esperados explicitamente. KAIROS_CORS_ORIGINS permite
# extender la lista en deploys.
_default_origins = [
    "http://localhost:5173",
    "http://localhost:8080",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:8080",
]
_env_origins = [o.strip() for o in os.getenv("KAIROS_CORS_ORIGINS", "").split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_default_origins + _env_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Incluimos los routers de la version 1
app.include_router(optimizer.router, prefix="/api/v1", tags=["optimizer"])
app.include_router(db_planes.router, prefix="/api/v1", tags=["db"])
app.include_router(auth.router, prefix="/api/v1", tags=["auth"])
app.include_router(users.router, prefix="/api/v1", tags=["users"])

@app.get("/")
async def root():
    """Endpoint de bienvenida, para ver si el boliche esta abierto."""
    return {
        "mensaje": "¡Bienvenido a Kairos! El motor esta encendido y regulando.",
        "docs": "/docs"
    }

@app.get("/health")
async def health_check():
    """Para chequear que no se haya roto nada groso."""
    return {"status": "ok", "motor": "v8_prescriptivo"}
