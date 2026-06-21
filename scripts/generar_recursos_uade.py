"""
Generador determinista de recursos operativos para Kairos.

Produce, a partir del plan real de UADE, tres datasets que alimentan las
nuevas restricciones del motor:

  - aulas.json            : capacidad y cantidad de aulas por turno.
  - docentes.json         : pool de docentes con materias que dictan y
                            disponibilidad horaria. Algunos quedan marcados
                            con horario NO fehaciente, para ejercitar la
                            estimacion via historico.
  - historico_dictado.json: cursos efectivamente dictados en cuatrimestres
                            anteriores (insumo de estimacion).

Es 100% determinista (sin random) para que el seed sea reproducible.

Uso:
    python scripts/generar_recursos_uade.py
"""

import hashlib
import json
from pathlib import Path
from typing import Dict, List

TURNOS = ["manana", "tarde", "noche"]

NOMBRES = [
    "Carlos", "Elena", "Martin", "Ana", "Lucas", "Sofia", "Jorge", "Maria",
    "Diego", "Laura", "Gabriel", "Patricia", "Sergio", "Valeria", "Hernan",
    "Carolina", "Pablo", "Florencia", "Ricardo", "Natalia",
]
APELLIDOS = [
    "Gomez", "Lopez", "Rodriguez", "Fernandez", "Gonzalez", "Perez",
    "Martinez", "Sanchez", "Diaz", "Alvarez", "Rossi", "Bianchi",
    "Romano", "Ferraro", "Castro", "Nunez", "Ibarra", "Acosta",
]


def _h(text: str) -> int:
    """Hash entero determinista (estable entre corridas y plataformas)."""
    return int(hashlib.md5(text.encode("utf-8")).hexdigest(), 16)


def generar_aulas() -> List[Dict]:
    """
    Aulas de distintas capacidades. La cantidad y capacidad son la restriccion
    dura: el motor no podra abrir mas comisiones por turno que aulas haya.
    """
    specs = [
        # (prefijo, capacidad, cantidad)
        ("Auditorio", 120, 1),
        ("Magna", 80, 2),
        ("Aula", 50, 6),
        ("Aula", 35, 8),
        ("Lab", 25, 4),
    ]
    aulas = []
    n = 1
    for prefijo, capacidad, cantidad in specs:
        for _ in range(cantidad):
            aula_id = f"AULA{n:03d}"
            aulas.append(
                {
                    "aula_id": aula_id,
                    "nombre": f"{prefijo} {n}",
                    "capacidad": capacidad,
                    "sede": "Monserrat",
                    # Todas sirven en los 3 turnos (una misma aula, distintas franjas).
                    "turnos_disponibles": list(TURNOS),
                }
            )
            n += 1
    return aulas


def generar_docentes_e_historico(plan: Dict):
    """
    Arma el pool de docentes y el historico de dictado, ambos coherentes con
    las materias del plan. Cada docente dicta 2-3 materias contiguas; algunos
    quedan sin horario fehaciente para que el motor estime con el historico.
    """
    materias = list(plan["materias"].items())  # [(codigo, materia), ...]
    materias.sort(key=lambda kv: (kv[1]["ano"], kv[1]["cuatrimestre"], kv[0]))

    docentes: List[Dict] = []
    historico: List[Dict] = []

    # Pool dimensionado a la demanda: ~1 docente cada 1.4 materias. Cada docente
    # dicta un bloque de 3 materias contiguas (en orden año/cuatri), de modo que
    # cada materia queda cubierta por ~2 docentes con arranques distintos. Asi el
    # pool no sobra (no quedan docentes ociosos) pero alcanza para abrir las
    # comisiones de cada materia en sus distintos turnos.
    n_docentes = max(1, round(len(materias) / 1.4))
    hist_id = 1
    for idx in range(n_docentes):
        # Arranque del bloque repartido uniformemente sobre el plan.
        inicio = (idx * len(materias)) // n_docentes
        bloque = materias[inicio : inicio + 3] or materias[-3:]
        did = f"DOC{idx + 1:03d}"
        nombre = f"{NOMBRES[_h(did) % len(NOMBRES)]} {APELLIDOS[_h(did + 'a') % len(APELLIDOS)]}"
        titulo = ["Dr.", "Dra.", "Ing.", "Lic.", "Mg."][_h(did) % 5]
        nombre = f"{titulo} {nombre}"

        codigos = [c for c, _ in bloque]
        # Disponibilidad: cada docente cubre 2 turnos consecutivos, rotando con
        # el indice. Como hay ~2 docentes por materia con arranques distintos,
        # entre todos cubren los 3 turnos de cada materia.
        turnos_doc = [TURNOS[idx % 3], TURNOS[(idx + 1) % 3]]

        # 1 de cada 4 docentes no tiene horario fehaciente: su disponibilidad
        # declarada queda vacia y el motor la estima desde el historico.
        fehaciente = (idx % 4) != 0

        docentes.append(
            {
                "docente_id": did,
                "nombre": nombre,
                "materias_que_dicta": codigos,
                "disponibilidad_turnos": list(turnos_doc) if fehaciente else [],
                # Carga docente: 3 comisiones (4 para los de horario confirmado,
                # que tienen mas disponibilidad efectiva).
                "max_comisiones": 4 if fehaciente else 3,
                "horario_fehaciente": fehaciente,
            }
        )

        # Historico: cada docente dicto sus materias los 2 cuatrimestres previos.
        for (codigo, materia) in bloque:
            for (ano, cuatri) in [(2025, 1), (2025, 2)]:
                turno = turnos_doc[_h(f"{did}{codigo}{ano}{cuatri}") % len(turnos_doc)]
                historico.append(
                    {
                        "historico_id": f"H{hist_id:04d}",
                        "docente_id": did,
                        "docente_nombre": nombre,
                        "codigo_materia": codigo,
                        "nombre_materia": materia["nombre"],
                        "turno": turno,
                        "ano": ano,
                        "cuatrimestre": cuatri,
                        "cantidad_alumnos": 20 + (_h(f"{codigo}{cuatri}") % 35),
                    }
                )
                hist_id += 1

    return docentes, historico


def main() -> int:
    root = Path(__file__).parent.parent
    plan_path = next(
        p
        for p in [root / "data" / "raw" / "plan_uade_api.json", root / "plan_estudio_ing_informatica.json"]
        if p.exists()
    )
    plan = json.loads(plan_path.read_text(encoding="utf-8"))

    out_dir = root / "data" / "raw"
    out_dir.mkdir(parents=True, exist_ok=True)

    aulas = generar_aulas()
    docentes, historico = generar_docentes_e_historico(plan)

    (out_dir / "aulas_uade.json").write_text(
        json.dumps(aulas, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    (out_dir / "docentes_uade.json").write_text(
        json.dumps(docentes, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    (out_dir / "historico_dictado_uade.json").write_text(
        json.dumps(historico, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    sin_horario = sum(1 for d in docentes if not d["horario_fehaciente"])
    print(
        f"Generados: {len(aulas)} aulas, {len(docentes)} docentes "
        f"({sin_horario} sin horario fehaciente), {len(historico)} registros de historico."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
