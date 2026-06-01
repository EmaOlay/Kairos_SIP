"""
Seed de la DB con el plan de Ing. en Informatica de UADE.

Uso (dentro del container):
    python scripts/seed_db.py

Idempotente: si el plan ya existe, lo regraba.
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from kairos.db.session import SessionLocal
from kairos.db.repository import PlanRepository
from kairos.etl.ingester import DataIngester


def main() -> int:
    root = Path(__file__).parent.parent
    candidatos = [
        root / "data" / "raw" / "plan_uade_api.json",
        root / "plan_estudio_ing_informatica.json",
    ]
    plan_path = next((p for p in candidatos if p.exists()), None)
    if plan_path is None:
        print(f"ERROR: no se encontro el plan en: {candidatos}")
        return 1

    print(f"Cargando plan desde {plan_path}...")
    ingester = DataIngester()
    plan = ingester.cargar_plan_estudio(plan_path)

    session = SessionLocal()
    try:
        repo = PlanRepository(session)
        repo.upsert(plan)
        print(
            f"Plan '{plan.nombre_carrera}' (codigo {plan.codigo_plan}) "
            f"persistido con {len(plan.materias)} materias."
        )
    finally:
        session.close()

    return 0


if __name__ == "__main__":
    sys.exit(main())
