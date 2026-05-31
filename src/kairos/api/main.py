"""
Punto de entrada de la API REST de Kairos

Aca configuramos el boliche: FastAPI, los routers y los middlewares.
Es el cerebro que comunica el motor con el mundo exterior.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from kairos.api.v1.endpoints import optimizer

app = FastAPI(
    title="Kairos API",
    description="Motor de Analitica Prescriptiva para Optimizacion Academica",
    version="0.1.0",
)

# Configuramos los CORS para que no nos saquen cagando desde el front
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Incluimos los routers de la version 1
app.include_router(optimizer.router, prefix="/api/v1", tags=["optimizer"])

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
