"""
Script para levantar la API de Kairos

Usa uvicorn para correr la app de FastAPI.
Podes correrlo con: python scripts/run_api.py
"""

import subprocess
import uvicorn
import os
import sys

# Agregamos src al path por si las moscas
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "src"))


def _aplicar_migraciones() -> None:
    """
    Corre `alembic upgrade head` antes de levantar la API.

    Asi la DB queda siempre al dia con el esquema (incluidas las tablas de
    aulas/docentes/historico). Sin esto, un `docker compose up` sobre una DB
    en una version vieja hace fallar los endpoints que consultan esas tablas.
    Si falla (ej. DB todavia no lista), avisamos pero no abortamos: uvicorn
    reintenta y el healthcheck del compose espera a la DB.
    """
    root = os.path.join(os.path.dirname(__file__), "..")
    try:
        print("Aplicando migraciones (alembic upgrade head)...")
        subprocess.run(["alembic", "upgrade", "head"], cwd=root, check=True)
        print("Migraciones al dia.")
    except Exception as e:  # noqa: BLE001
        print(f"AVISO: no se pudieron aplicar las migraciones automaticamente: {e}")


if __name__ == "__main__":
    print("Levantando el boliche de Kairos...")
    _aplicar_migraciones()
    uvicorn.run(
        "kairos.api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
