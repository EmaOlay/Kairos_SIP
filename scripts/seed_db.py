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
from kairos.db.repository import (
    AulaRepository,
    DocenteRepository,
    EstudianteRepository,
    HistoricoRepository,
    PlanRepository,
)
from kairos.etl.ingester import DataIngester
from kairos.schemas.data_models import (
    Aula,
    Docente,
    EstudianteTrayectoria,
    HistoricoDictado,
)


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


def _cargar_json(path: Path):
    if not path.exists():
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _seed_recursos_operativos(session) -> None:
    """
    Carga aulas, docentes e historico de dictado. Si los datasets no existen
    todavia, los genera con scripts/generar_recursos_uade.py.
    """
    root = Path(__file__).parent.parent
    raw = root / "data" / "raw"
    aulas_path = raw / "aulas_uade.json"
    docentes_path = raw / "docentes_uade.json"
    historico_path = raw / "historico_dictado_uade.json"

    if not (aulas_path.exists() and docentes_path.exists() and historico_path.exists()):
        print("Datasets de recursos no encontrados, generandolos...")
        import generar_recursos_uade  # mismo directorio scripts/

        generar_recursos_uade.main()

    # Reemplazo total: limpiamos las tablas operativas antes de recargar, asi
    # un dataset mas chico no deja registros huerfanos de una corrida anterior.
    from kairos.db.models import AulaORM, DocenteORM, HistoricoDictadoORM
    from sqlalchemy import delete

    for orm in (AulaORM, DocenteORM, HistoricoDictadoORM):
        session.execute(delete(orm))
    session.commit()

    aulas = _cargar_json(aulas_path) or []
    aula_repo = AulaRepository(session)
    for item in aulas:
        try:
            aula_repo.upsert(Aula(**item))
        except ValidationError as e:
            print(f"  Aula rechazada {item.get('aula_id', '?')}: {e.error_count()} errores")
    print(f"Aulas persistidas: {len(aulas)}.")

    docentes = _cargar_json(docentes_path) or []
    doc_repo = DocenteRepository(session)
    for item in docentes:
        try:
            doc_repo.upsert(Docente(**item))
        except ValidationError as e:
            print(f"  Docente rechazado {item.get('docente_id', '?')}: {e.error_count()} errores")
    sin_horario = sum(1 for d in docentes if not d.get("horario_fehaciente", True))
    print(f"Docentes persistidos: {len(docentes)} ({sin_horario} sin horario fehaciente).")

    historico = _cargar_json(historico_path) or []
    hist_repo = HistoricoRepository(session)
    for item in historico:
        try:
            hist_repo.upsert(HistoricoDictado(**item))
        except ValidationError as e:
            print(f"  Historico rechazado {item.get('historico_id', '?')}: {e.error_count()} errores")
    print(f"Registros de historico persistidos: {len(historico)}.")


def main() -> int:
    session = SessionLocal()
    try:
        _seed_plan(session)
        _seed_estudiantes(session)
        _seed_recursos_operativos(session)
    finally:
        session.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
