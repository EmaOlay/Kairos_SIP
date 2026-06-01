"""
Seed de la DB con el plan de Ing. en Informatica de UADE
y los estudiantes de prueba.

Uso (dentro del container):
    python scripts/seed_db.py

Idempotente: si el plan o los estudiantes ya existen, los regraba.
"""

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from pydantic import ValidationError

from kairos.db.session import SessionLocal
from kairos.db.repository import EstudianteRepository, PlanRepository
from kairos.etl.ingester import DataIngester
from kairos.schemas.data_models import EstudianteTrayectoria


def _seed_plan(session) -> str:
    root = Path(__file__).parent.parent
    candidatos = [
        root / "data" / "raw" / "plan_uade_api.json",
        root / "plan_estudio_ing_informatica.json",
    ]
    plan_path = next((p for p in candidatos if p.exists()), None)
    if plan_path is None:
        raise FileNotFoundError(f"No se encontro el plan en: {candidatos}")

    print(f"Cargando plan desde {plan_path}...")
    ingester = DataIngester()
    plan = ingester.cargar_plan_estudio(plan_path)

    repo = PlanRepository(session)
    repo.upsert(plan)
    print(
        f"Plan '{plan.nombre_carrera}' (codigo {plan.codigo_plan}) "
        f"persistido con {len(plan.materias)} materias."
    )
    return plan.codigo_plan


def _seed_estudiantes(session) -> None:
    root = Path(__file__).parent.parent
    estudiantes_path = root / "data" / "raw" / "estudiantes_uade.json"
    if not estudiantes_path.exists():
        print(f"AVISO: no se encontro {estudiantes_path}, salteo estudiantes.")
        return

    print(f"Cargando estudiantes desde {estudiantes_path}...")
    with open(estudiantes_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    repo = EstudianteRepository(session)
    persistidos = 0
    rechazados = 0
    for item in data:
        try:
            est = EstudianteTrayectoria(**item)
        except ValidationError as e:
            rechazados += 1
            print(f"  Rechazado {item.get('estudiante_id', '?')}: {e.error_count()} errores")
            continue
        repo.upsert(est)
        persistidos += 1

    print(f"Estudiantes persistidos: {persistidos} (rechazados: {rechazados}).")


def main() -> int:
    session = SessionLocal()
    try:
        _seed_plan(session)
        _seed_estudiantes(session)
    finally:
        session.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
