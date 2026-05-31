"""
Modulo ETL: Ingesta, validacion y limpieza de datasets para Kairos

Procesa archivos planos (CSV, JSON) con trayectorias estudiantiles,
planes de estudio y recursos disponibles. Valida tipos y estructura
mediante Pydantic, y retorna objetos listos para el motor de optimizacion.
"""

import json
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from datetime import datetime
import logging

import pandas as pd
from pydantic import ValidationError

from kairos.schemas.data_models import (
    EstudianteTrayectoria,
    RegistroTrayectoria,
    PlanEstudio,
    Materia,
    RecursoDisponible,
    EstadoMateria,
)


# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DataIngester:
    """
    Ingesta y valida datasets para Kairos.
    
    Maneja la lectura de archivos planos, validacion de esquemas mediante Pydantic,
    limpieza de registros invalidos, y retorna estructuras tipadas listas
    para procesamiento.
    """

    def __init__(self, data_dir: Path = Path("data/raw")):
        self.data_dir = Path(data_dir)
        self.estudiantes: Dict[str, EstudianteTrayectoria] = {}
        self.plan_estudio: Optional[PlanEstudio] = None
        self.recursos: List[RecursoDisponible] = []
        self.errores_validacion: List[Dict] = []

    def cargar_plan_estudio(self, ruta_json: Path) -> PlanEstudio:
        """
        Carga un plan de estudio desde JSON.
        
        El JSON debe tener estructura:
        {
            "codigo_plan": "1621",
            "nombre_carrera": "Ingenieria en Informatica",
            "ano_vigencia": 2021,
            "duracion_anos": 5,
            "materias": {
                "3.4.069": {
                    "codigo": "3.4.069",
                    "nombre": "Fundamentos de Informatica",
                    "ano": 1,
                    "cuatrimestre": 1,
                    ...
                },
                ...
            }
        }
        """
        logger.info(f"Cargando plan de estudio desde: {ruta_json}")

        try:
            with open(ruta_json, "r", encoding="utf-8") as f:
                data = json.load(f)

            # Convertir lista de materias a diccionario si es necesario
            if "materias" in data and isinstance(data["materias"], list):
                materias_dict = {m["codigo"]: m for m in data["materias"]}
                data["materias"] = materias_dict

            # Validar con Pydantic
            self.plan_estudio = PlanEstudio(**data)

            logger.info(
                f" Plan cargado: {self.plan_estudio.nombre_carrera} "
                f"({len(self.plan_estudio.materias)} materias)"
            )

            return self.plan_estudio

        except json.JSONDecodeError as e:
            logger.error(f"Error al parsear JSON: {e}")
            raise
        except ValidationError as e:
            logger.error(f"Error de validacion en plan de estudio: {e}")
            raise

    def cargar_trayectorias_estudiantes(
        self, ruta_csv: Path
    ) -> Dict[str, EstudianteTrayectoria]:
        """
        Carga trayectorias de estudiantes desde CSV.
        
        CSV esperado:
        | estudiante_id | codigo_carrera | plan_estudio_id | ano_ingreso |
        |               |                |                 |             |
        | EST001        | ING_INF        | 1621            | 2020        |
        
        Nota: Este loader espera un CSV adicional con los registros individuales
        (ver _cargar_registros_trayectoria).
        """
        logger.info(f"Cargando trayectorias desde: {ruta_csv}")

        try:
            df = pd.read_csv(ruta_csv, dtype={"estudiante_id": str})

            # Limpiar: remover duplicados por estudiante_id
            df = df.drop_duplicates(subset=["estudiante_id"])

            for _, row in df.iterrows():
                try:
                    est = EstudianteTrayectoria(
                        estudiante_id=str(row["estudiante_id"]),
                        codigo_carrera=str(row["codigo_carrera"]),
                        plan_estudio_id=str(row["plan_estudio_id"]),
                        ano_ingreso=int(row["ano_ingreso"]),
                        registros_trayectoria=[],
                    )
                    self.estudiantes[est.estudiante_id] = est

                except ValidationError as e:
                    self.errores_validacion.append(
                        {
                            "tipo": "EstudianteTrayectoria",
                            "fila": _,
                            "error": str(e),
                            "data": row.to_dict(),
                        }
                    )
                    logger.warning(f"Fila {_} invalida: {e.error_count()} errores")

            logger.info(
                f" {len(self.estudiantes)} estudiantes cargados "
                f"({len(self.errores_validacion)} rechazados)"
            )

            return self.estudiantes

        except FileNotFoundError:
            logger.error(f"Archivo no encontrado: {ruta_csv}")
            raise
        except Exception as e:
            logger.error(f"Error cargando trayectorias: {e}")
            raise

    def cargar_registros_trayectoria(self, ruta_csv: Path) -> Dict[str, EstudianteTrayectoria]:
        """
        Carga registros individuales de materias cursadas/aprobadas.
        
        CSV esperado:
        | estudiante_id | codigo_materia | nombre_materia | estado    | ano_academico |
        |               |                |                |           |               |
        | EST001        | 3.4.069        | Fund. Informatica | aprobada  | 2020          |
        """
        logger.info(f"Cargando registros de trayectoria desde: {ruta_csv}")

        try:
            df = pd.read_csv(ruta_csv, dtype={"estudiante_id": str, "codigo_materia": str})

            registros_por_estudiante = df.groupby("estudiante_id")

            for est_id, grupo in registros_por_estudiante:
                if est_id not in self.estudiantes:
                    logger.warning(f"Estudiante {est_id} no existe. Creando entrada.")
                    self.estudiantes[est_id] = EstudianteTrayectoria(
                        estudiante_id=est_id,
                        codigo_carrera="UNKNOWN",
                        plan_estudio_id="UNKNOWN",
                        ano_ingreso=2020,
                    )

                for _, row in grupo.iterrows():
                    try:
                        # Parse fecha si existe
                        fecha = None
                        if pd.notna(row.get("fecha_aprobacion")):
                            fecha = pd.to_datetime(row["fecha_aprobacion"])

                        registro = RegistroTrayectoria(
                            codigo_materia=str(row["codigo_materia"]),
                            nombre_materia=str(row["nombre_materia"]),
                            estado=EstadoMateria(row["estado"].lower()),
                            ano_academico=int(row["ano_academico"]),
                            cuatrimestre=int(row.get("cuatrimestre", 1)),
                            calificacion=float(row["calificacion"])
                            if pd.notna(row.get("calificacion"))
                            else None,
                            fecha_aprobacion=fecha,
                        )

                        self.estudiantes[est_id].registros_trayectoria.append(registro)

                    except (ValidationError, ValueError) as e:
                        self.errores_validacion.append(
                            {
                                "tipo": "RegistroTrayectoria",
                                "estudiante_id": est_id,
                                "fila": _,
                                "error": str(e),
                                "data": row.to_dict(),
                            }
                        )

            logger.info(
                f" {len(self.estudiantes)} estudiantes con registros "
                f"({len(self.errores_validacion)} registros rechazados)"
            )

            return self.estudiantes

        except FileNotFoundError:
            logger.error(f"Archivo no encontrado: {ruta_csv}")
            raise

    def cargar_recursos_disponibles(self, ruta_csv: Path) -> List[RecursoDisponible]:
        """
        Carga recursos disponibles (comisiones, cupos, horarios).
        
        CSV esperado:
        | recurso_id | codigo_materia | nombre_materia | ano_academico | cupos_totales |
        |            |                |                |               |               |
        | COM001     | 3.4.069        | Fund. Informatica | 2025          | 50            |
        """
        logger.info(f"Cargando recursos disponibles desde: {ruta_csv}")

        try:
            df = pd.read_csv(ruta_csv)

            for _, row in df.iterrows():
                try:
                    # Parse lista de dias (si viene en string)
                    dias = []
                    if pd.notna(row.get("dias_semana")):
                        dias_str = row["dias_semana"]
                        if isinstance(dias_str, str):
                            dias = [d.strip() for d in dias_str.split(",")]

                    recurso = RecursoDisponible(
                        recurso_id=str(row["recurso_id"]),
                        codigo_materia=str(row["codigo_materia"]),
                        nombre_materia=str(row["nombre_materia"]),
                        ano_academico=int(row["ano_academico"]),
                        cuatrimestre=int(row.get("cuatrimestre", 1)),
                        cupos_totales=int(row["cupos_totales"]),
                        cupos_ocupados=int(row.get("cupos_ocupados", 0)),
                        modalidad=str(row.get("modalidad", "presencial")),
                        horario_inicio=str(row.get("horario_inicio", "09:00")),
                        horario_fin=str(row.get("horario_fin", "12:00")),
                        dias_semana=dias,
                        docente_id=row.get("docente_id") if pd.notna(row.get("docente_id")) else None,
                        docente_nombre=row.get("docente_nombre")
                        if pd.notna(row.get("docente_nombre"))
                        else None,
                        costo_operativo_base=float(row["costo_operativo_base"])
                        if pd.notna(row.get("costo_operativo_base"))
                        else None,
                        costo_por_alumno=float(row["costo_por_alumno"])
                        if pd.notna(row.get("costo_por_alumno"))
                        else None,
                    )
                    self.recursos.append(recurso)

                except (ValidationError, ValueError) as e:
                    self.errores_validacion.append(
                        {
                            "tipo": "RecursoDisponible",
                            "fila": _,
                            "error": str(e),
                            "data": row.to_dict(),
                        }
                    )

            logger.info(
                f" {len(self.recursos)} recursos cargados "
                f"({len([e for e in self.errores_validacion if e['tipo'] == 'RecursoDisponible'])} rechazados)"
            )

            return self.recursos

        except FileNotFoundError:
            logger.error(f"Archivo no encontrado: {ruta_csv}")
            raise

    def validar_integridad(self) -> Tuple[bool, List[str]]:
        """
        Valida la integridad del dataset completo.
        
        Chequea:
        - Que todas las materias en registros existan en el plan
        - Que todos los estudiantes tengan plan valido
        - Consistencia en anos/cuatrimestres
        """
        problemas = []

        if self.plan_estudio is None:
            problemas.append("No se cargo plan de estudio")
            return (len(problemas) == 0, problemas)

        # Validar materias en registros
        for est_id, est in self.estudiantes.items():
            for registro in est.registros_trayectoria:
                if registro.codigo_materia not in self.plan_estudio.materias:
                    problemas.append(
                        f"Estudiante {est_id}: materia {registro.codigo_materia} no existe en plan"
                    )

        # Validar materias en recursos
        for recurso in self.recursos:
            if recurso.codigo_materia not in self.plan_estudio.materias:
                problemas.append(
                    f"Recurso {recurso.recurso_id}: materia {recurso.codigo_materia} no existe"
                )

        logger.info(f"Validacion: {' OK' if not problemas else f' {len(problemas)} problemas'}")

        return (len(problemas) == 0, problemas)

    def generar_reporte_errores(self) -> str:
        """Genera reporte de errores de validacion"""
        if not self.errores_validacion:
            return " Sin errores de validacion"

        reporte = [f"\n{'='*70}", "REPORTE DE ERRORES DE VALIDACION"]
        reporte.append(f"{'='*70}\n")

        por_tipo = {}
        for err in self.errores_validacion:
            tipo = err["tipo"]
            if tipo not in por_tipo:
                por_tipo[tipo] = []
            por_tipo[tipo].append(err)

        for tipo, errores in por_tipo.items():
            reporte.append(f"\n{tipo}: {len(errores)} errores")
            for err in errores[:5]:  # Mostrar primeros 5
                reporte.append(f"  - {err.get('error', 'Error desconocido')}")
            if len(errores) > 5:
                reporte.append(f"  ... y {len(errores) - 5} mas")

        reporte.append(f"\n{'='*70}\n")
        return "\n".join(reporte)
