"""
Generador determinista de estudiantes para Kairos.

Produce trayectorias COHERENTES con las correlatividades del plan: un alumno
solo puede tener aprobada una materia si ya aprobó sus prerequisitos. Cada
alumno avanza hasta cierto punto de la carrera segun su perfil y antiguedad,
dejando un frente de materias "disponibles" que generan demanda real.

Con volumen (cientos de alumnos) y avance escalonado, la demanda se reparte
por toda la carrera, de modo que se abren muchas comisiones y el pool de
docentes se ocupa (en vez de quedar casi todos libres).

100% determinista (sin random) para que el seed sea reproducible.

Uso:
    python scripts/generar_estudiantes_uade.py [cantidad]
"""

import hashlib
import json
import sys
from pathlib import Path
from typing import Dict, List

TURNOS = ["manana", "tarde", "noche"]
# Distribucion de preferencia de turno (la noche es la mas demandada en UADE).
TURNO_WEIGHTS = ["noche", "noche", "noche", "noche", "tarde", "tarde", "tarde", "manana", "manana"]


def _h(text: str) -> int:
    return int(hashlib.md5(text.encode("utf-8")).hexdigest(), 16)


def _orden_topologico(materias: Dict[str, dict]) -> List[str]:
    """
    Ordena las materias respetando correlatividades (Kahn). Si una materia
    referencia un prereq que no esta en el plan, lo ignora. Ante un ciclo
    (no deberia pasar en un plan valido) corta y agrega lo que quede.
    """
    pendientes = {c: set(m.get("correlativas_anteriores", [])) & set(materias) for c, m in materias.items()}
    orden: List[str] = []
    # Orden estable por (año, cuatri, codigo) para determinismo.
    cola = sorted(
        [c for c, deps in pendientes.items() if not deps],
        key=lambda c: (materias[c]["ano"], materias[c]["cuatrimestre"], c),
    )
    vistos = set(cola)
    while cola:
        c = cola.pop(0)
        orden.append(c)
        nuevos = []
        for otro, deps in pendientes.items():
            if otro in vistos:
                continue
            deps.discard(c)
            if not deps:
                nuevos.append(otro)
        for n in sorted(nuevos, key=lambda c: (materias[c]["ano"], materias[c]["cuatrimestre"], c)):
            vistos.add(n)
            cola.append(n)
    # Por las dudas: agregar materias que hayan quedado afuera (ciclos).
    for c in materias:
        if c not in orden:
            orden.append(c)
    return orden


def generar_estudiantes(plan: Dict, cantidad: int) -> List[Dict]:
    materias = plan["materias"]
    plan_id = plan.get("codigo_plan") or plan.get("plan") or "1621"
    orden = _orden_topologico(materias)
    total = len(orden)

    # Perfiles: fraccion de la carrera que avanzaron y prob de aprobar lo cursado.
    # (avance_min, avance_max, prob_aprobar)
    perfiles = [
        ("avanzado", 0.65, 0.95, 0.9),
        ("intermedio", 0.35, 0.7, 0.75),
        ("inicial", 0.1, 0.4, 0.7),
        ("rezagado", 0.05, 0.25, 0.5),
    ]

    estudiantes: List[Dict] = []
    for i in range(cantidad):
        sid = f"EST{i:04d}"
        seed = _h(sid)
        perfil = perfiles[seed % len(perfiles)]
        _, av_min, av_max, prob_aprobar = perfil

        # Fraccion de avance del alumno dentro del orden topologico.
        frac = av_min + ((seed >> 3) % 1000) / 1000.0 * (av_max - av_min)
        hasta = max(1, int(total * frac))

        ano_ingreso = 2019 + (seed % 6)  # 2019..2024
        turno = TURNO_WEIGHTS[(seed >> 5) % len(TURNO_WEIGHTS)]

        registros = []
        for pos, codigo in enumerate(orden[:hasta]):
            mat = materias[codigo]
            # Determinismo por (alumno, materia).
            r = (_h(f"{sid}:{codigo}") % 1000) / 1000.0
            if r < prob_aprobar:
                estado = "aprobada"
                # Nota entre 4 y 10, determinista.
                nota = 4 + (_h(f"nota:{sid}:{codigo}") % 61) / 10.0
                registros.append(
                    {
                        "codigo_materia": codigo,
                        "nombre_materia": mat["nombre"],
                        "estado": "aprobada",
                        "ano_academico": min(2025, ano_ingreso + pos // 8),
                        "cuatrimestre": 1 + (pos % 2),
                        "calificacion": round(nota, 1),
                    }
                )
            elif r < prob_aprobar + 0.15:
                # Regular (cursada aprobada, final pendiente): no habilita prereqs.
                registros.append(
                    {
                        "codigo_materia": codigo,
                        "nombre_materia": mat["nombre"],
                        "estado": "regular",
                        "ano_academico": min(2025, ano_ingreso + pos // 8),
                        "cuatrimestre": 1 + (pos % 2),
                        "calificacion": None,
                    }
                )
            # else: ni cursó (queda como demanda futura).

        estudiantes.append(
            {
                "estudiante_id": sid,
                "codigo_carrera": "ING_INF",
                "plan_estudio_id": plan_id,
                "ano_ingreso": ano_ingreso,
                "turno_preferido": turno,
                "registros_trayectoria": registros,
            }
        )
    return estudiantes


def main() -> int:
    cantidad = int(sys.argv[1]) if len(sys.argv) > 1 else 400
    root = Path(__file__).parent.parent
    plan_path = next(
        p
        for p in [root / "data" / "raw" / "plan_uade_api.json", root / "plan_estudio_ing_informatica.json"]
        if p.exists()
    )
    plan = json.loads(plan_path.read_text(encoding="utf-8"))

    estudiantes = generar_estudiantes(plan, cantidad)

    out = root / "data" / "raw" / "estudiantes_uade.json"
    out.write_text(json.dumps(estudiantes, indent=2, ensure_ascii=False), encoding="utf-8")

    aprob = sum(
        1 for e in estudiantes for r in e["registros_trayectoria"] if r["estado"] == "aprobada"
    )
    print(
        f"Generados {len(estudiantes)} estudiantes "
        f"({aprob} materias aprobadas en total, "
        f"{aprob // max(1, len(estudiantes))} promedio por alumno)."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
