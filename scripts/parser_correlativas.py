"""
Script para parsear HTML de correlativas UADE y generar estructura de datos
"""

import re
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, asdict
import json


@dataclass
class Materia:
    """Representa una materia en el plan de estudios"""
    codigo: str
    nombre: str
    ano: int
    cuatrimestre: int
    correlativas_anteriores: List[str] = None
    correlativas_posteriores: List[str] = None

    def __post_init__(self):
        if self.correlativas_anteriores is None:
            self.correlativas_anteriores = []
        if self.correlativas_posteriores is None:
            self.correlativas_posteriores = []


class CorrelativasParser:
    """Parser para extraer correlativas de HTML UADE"""

    def __init__(self, html_path: str):
        self.html_path = Path(html_path)
        self.materias: Dict[str, Materia] = {}
        self.carrera = ""

    def parse(self) -> Dict[str, Materia]:
        """Parsea el HTML y retorna un diccionario de materias"""
        with open(self.html_path, "r", encoding="utf-8") as f:
            html = f.read()

        # Extraer titulo de carrera
        carrera_match = re.search(
            r'<span id="[^"]*_lbl_TituloCarrera"[^>]*>([^<]+)</span>',
            html
        )
        if carrera_match:
            self.carrera = carrera_match.group(1).strip()
            print(f" Carrera: {self.carrera}")

        # Extraer todas las materias con sus codigos y nombres
        self._extract_materias(html)

        # Extraer correlativas
        self._extract_correlativas(html)

        return self.materias

    def _extract_materias(self, html: str) -> None:
        """Extrae codigo, nombre, ano y cuatrimestre de cada materia"""

        # Buscar anos (1 Ano, 2 Ano, etc)
        ano_pattern = r'<span>(\d+) Ano</span>'
        cuatrimestre_pattern = r'<span>(\d+) Cuatrimestre</span>'

        # Division por anos
        anos_bloques = re.split(r'<span>\d+ Ano</span>', html)

        ano_num = 0
        for ano_bloque in anos_bloques[1:]:  # Skip primer elemento (antes del primer ano)
            ano_num += 1

            # Division por cuatrimestres
            cuatri_bloques = re.split(
                r'<span>\d+ Cuatrimestre</span>',
                ano_bloque
            )

            cuatri_num = 0
            for cuatri_bloque in cuatri_bloques[1:]:  # Skip primer elemento

                cuatri_num += 1

                # Buscar materias en este cuatrimestre
                # Patron: <span>CODIGO</span> ... <span>NOMBRE</span>
                materia_pattern = r'<td class="materias2"[^>]*>\s*<span>([^<]+)</span>\s*</td>\s*<td class="materias">\s*<span>([^<]+)</span>\s*</td>'

                for match in re.finditer(materia_pattern, cuatri_bloque):
                    codigo = match.group(1).strip()
                    nombre = match.group(2).strip()

                    self.materias[codigo] = Materia(
                        codigo=codigo,
                        nombre=nombre,
                        ano=ano_num,
                        cuatrimestre=cuatri_num
                    )

    def _extract_correlativas(self, html: str) -> None:
        """Extrae correlativas anteriores y posteriores de cada materia"""

        # Para cada materia, buscar sus correlativas
        for codigo in list(self.materias.keys()):
            # Escapar el codigo para usarlo en regex
            codigo_escaped = re.escape(codigo)

            # Buscar la tabla de correlativas para esta materia
            # El patron ID puede ser: _2{codigo} o _2{codigo}1 (para materias con el mismo nombre)
            table_pattern = (
                rf'id="ctl00_ContentPlaceHolderMain_2{codigo_escaped}[^"]*"[^>]*>.*?</table>'
            )

            table_match = re.search(table_pattern, html, re.DOTALL)
            if table_match:
                table_html = table_match.group(0)

                # Extraer correlativas anteriores
                anterior_pattern = r'Correlativas Anteriores:\s*([^<]+)'
                anterior_match = re.search(anterior_pattern, table_html)
                if anterior_match:
                    anterior_text = anterior_match.group(1).strip()
                    if anterior_text != "No posee":
                        # Parsear codigos de materias (formato: "3.4.001, 3.4.002")
                        codigos = [c.strip() for c in anterior_text.split(",") if c.strip()]
                        self.materias[codigo].correlativas_anteriores = codigos

                # Extraer correlativas posteriores
                posterior_pattern = r'Correlativas Posteriores:\s*([^<]+)'
                posterior_match = re.search(posterior_pattern, table_html)
                if posterior_match:
                    posterior_text = posterior_match.group(1).strip()
                    if posterior_text != "No posee":
                        # Parsear codigos de materias
                        codigos = [c.strip() for c in posterior_text.split(",") if c.strip()]
                        self.materias[codigo].correlativas_posteriores = codigos

    def generar_estructura_json(self) -> str:
        """Genera JSON con la estructura de materias y correlativas"""
        estructura = {
            "carrera": self.carrera,
            "plan": "1621",
            "ano_vigencia": "2021",
            "materias": [
                {
                    "codigo": m.codigo,
                    "nombre": m.nombre,
                    "ano": m.ano,
                    "cuatrimestre": m.cuatrimestre,
                    "correlativas_anteriores": m.correlativas_anteriores,
                    "correlativas_posteriores": m.correlativas_posteriores,
                }
                for m in sorted(
                    self.materias.values(),
                    key=lambda x: (x.ano, x.cuatrimestre, x.codigo)
                )
            ]
        }
        return json.dumps(estructura, indent=2, ensure_ascii=False)

    def generar_resumen(self) -> str:
        """Genera un resumen textual de la estructura"""
        resumen = [
            f"\n{'='*70}",
            f"CARRERA: {self.carrera}",
            f"PLAN: 1621 - ANO VIGENCIA: 2021",
            f"{'='*70}\n",
        ]

        ano_actual = 0
        cuatri_actual = 0

        for materia in sorted(
            self.materias.values(),
            key=lambda x: (x.ano, x.cuatrimestre, x.codigo)
        ):
            if materia.ano != ano_actual:
                ano_actual = materia.ano
                cuatri_actual = 0
                resumen.append(f"\n{''*70}")
                resumen.append(f"{'' * 3} ANO {ano_actual} {'' * 3}")
                resumen.append(f"{''*70}")

            if materia.cuatrimestre != cuatri_actual:
                cuatri_actual = materia.cuatrimestre
                resumen.append(f"\n    CUATRIMESTRE {cuatri_actual}")

            resumen.append(
                f"       [{materia.codigo}] {materia.nombre}"
            )

        resumen.append(f"\n{'='*70}")
        resumen.append(f"TOTAL DE MATERIAS: {len(self.materias)}")
        resumen.append(f"{'='*70}\n")

        return "\n".join(resumen)


if __name__ == "__main__":
    import sys
    html_file = sys.argv[1] if len(sys.argv) > 1 else "data/raw/correlativas.html"
    parser = CorrelativasParser(html_file)
    materias = parser.parse()

    print(f"\n Se extrajeron {len(materias)} materias\n")

    # Generar resumen
    print(parser.generar_resumen())

    # Guardar estructura en JSON
    output_path = Path("plan_estudio_ing_informatica.json")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(parser.generar_estructura_json())

    print(f" Estructura guardada en: {output_path}\n")
