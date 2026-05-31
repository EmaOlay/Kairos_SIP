"""
Script para levantar la API de Kairos

Usa uvicorn para correr la app de FastAPI. 
Podes correrlo con: python scripts/run_api.py
"""

import uvicorn
import os
import sys

# Agregamos src al path por si las moscas
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "src"))

if __name__ == "__main__":
    print("Levantando el boliche de Kairos...")
    uvicorn.run(
        "kairos.api.main:app", 
        host="0.0.0.0", 
        port=8000, 
        reload=True,
        log_level="info"
    )
