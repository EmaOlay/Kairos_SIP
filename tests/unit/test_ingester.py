"""
Tests unitarios para kairos.etl.ingester

Fijate que aca probamos que la ingesta de datos no se rompa cuando le pasamos
archivos CSV o JSON. Es clave que el DataIngester se banque datos mal formateados
y nos avise que esta pasando, sin tirar la toalla de una.
"""

import pytest
import json
import pandas as pd
from pathlib import Path
from kairos.etl.ingester import DataIngester
from kairos.schemas.data_models import PlanEstudio, EstadoMateria


class TestDataIngester:
    """
    Suite de tests para el DataIngester.
    
    Chequeamos que cargue bien los planes, los pibes (estudiantes) y los recursos.
    Ojo con los paths y los formatos de los archivos, que no se nos escape nada.
    """

    @pytest.fixture
    def ingester(self):
        """Fixture para tener un ingester limpito en cada test"""
        return DataIngester()

    def test_cargar_plan_estudio_valido(self, ingester, tmp_path):
        """
        Verifica que carga un JSON de plan de estudio como la gente.
        """
        plan_data = {
            "codigo_plan": "1621",
            "nombre_carrera": "Ingenieria en Informatica",
            "facultad": "Ingenieria",
            "ano_vigencia": 2021,
            "duracion_anos": 5,
            "total_creditos": 150,
            "materias": [
                {
                    "codigo": "3.4.069",
                    "nombre": "Fundamentos de Informatica",
                    "ano": 1,
                    "cuatrimestre": 1,
                    "horas_teoricas": 30,
                    "horas_practicas": 30,
                    "creditos": 6
                }
            ]
        }
        
        ruta_json = tmp_path / "plan.json"
        with open(ruta_json, "w", encoding="utf-8") as f:
            json.dump(plan_data, f)
            
        plan = ingester.cargar_plan_estudio(ruta_json)
        
        assert plan.codigo_plan == "1621"
        assert "3.4.069" in plan.materias
        assert plan.materias["3.4.069"].nombre == "Fundamentos de Informatica"

    def test_cargar_trayectorias_estudiantes_csv(self, ingester, tmp_path):
        """
        Chequea que chupe bien los datos de los estudiantes desde un CSV.
        """
        csv_data = (
            "estudiante_id,codigo_carrera,plan_estudio_id,ano_ingreso\n"
            "EST001,ING_INF,1621,2023\n"
            "EST002,ING_INF,1621,2022\n"
        )
        ruta_csv = tmp_path / "estudiantes.csv"
        ruta_csv.write_text(csv_data)
        
        estudiantes = ingester.cargar_trayectorias_estudiantes(ruta_csv)
        
        assert len(estudiantes) == 2
        assert "EST001" in estudiantes
        assert estudiantes["EST001"].ano_ingreso == 2023

    def test_cargar_registros_trayectoria_csv(self, ingester, tmp_path):
        """
        Prueba que cargue los registros de las materias que ya metieron los pibes.
        """
        # No hace falta setearlo en None, que el ingester se encargue de crearlo si no esta

        csv_data = (
            "estudiante_id,codigo_materia,nombre_materia,estado,ano_academico,cuatrimestre,calificacion\n"
            "EST001,3.4.069,Fund. Informatica,aprobada,2023,1,8.5\n"
            "EST001,3.4.070,Estructura de Datos,inscripta,2024,1,\n"
        )
        ruta_csv = tmp_path / "registros.csv"
        ruta_csv.write_text(csv_data)
        
        estudiantes = ingester.cargar_registros_trayectoria(ruta_csv)
        
        assert len(estudiantes["EST001"].registros_trayectoria) == 2
        reg1 = estudiantes["EST001"].registros_trayectoria[0]
        assert reg1.codigo_materia == "3.4.069"
        assert reg1.estado == EstadoMateria.APROBADA
        assert reg1.calificacion == 8.5

    def test_cargar_recursos_disponibles_csv(self, ingester, tmp_path):
        """
        Verifica que los recursos (comisiones y demas) se carguen sin romperse.
        """
        csv_data = (
            "recurso_id,codigo_materia,nombre_materia,ano_academico,cuatrimestre,cupos_totales,cupos_ocupados\n"
            "COM001,3.4.069,Fund. Informatica,2025,1,50,30\n"
        )
        ruta_csv = tmp_path / "recursos.csv"
        ruta_csv.write_text(csv_data)
        
        recursos = ingester.cargar_recursos_disponibles(ruta_csv)
        
        assert len(recursos) == 1
        assert recursos[0].recurso_id == "COM001"
        assert recursos[0].cupos_totales == 50

    def test_validar_integridad_ok(self, ingester, tmp_path, plan_estudio_minimo):
        """
        Aca vemos si la validacion de integridad se porta bien cuando todo esta en orden.
        """
        ingester.plan_estudio = plan_estudio_minimo
        
        # Agregamos un estudiante con una materia que SI esta en el plan
        from kairos.schemas.data_models import EstudianteTrayectoria, RegistroTrayectoria
        est = EstudianteTrayectoria(
            estudiante_id="EST001",
            codigo_carrera="ING_INF",
            plan_estudio_id="1621",
            ano_ingreso=2023,
            registros_trayectoria=[
                RegistroTrayectoria(
                    codigo_materia="3.4.069",
                    nombre_materia="Fundamentos de Informatica",
                    estado=EstadoMateria.APROBADA,
                    ano_academico=2023,
                    cuatrimestre=1
                )
            ]
        )
        ingester.estudiantes["EST001"] = est
        
        valido, problemas = ingester.validar_integridad()
        
        assert valido is True
        assert len(problemas) == 0

    def test_validar_integridad_falla_materia_inexistente(self, ingester, plan_estudio_minimo):
        """
        Chequeamos que salte el error si un pibe tiene una materia que no figura en el plan.
        """
        ingester.plan_estudio = plan_estudio_minimo
        
        from kairos.schemas.data_models import EstudianteTrayectoria, RegistroTrayectoria
        est = EstudianteTrayectoria(
            estudiante_id="EST001",
            codigo_carrera="ING_INF",
            plan_estudio_id="1621",
            ano_ingreso=2023,
            registros_trayectoria=[
                RegistroTrayectoria(
                    codigo_materia="9.9.999", # Esta no esta en el plan_estudio_minimo
                    nombre_materia="Materia Fantasma",
                    estado=EstadoMateria.APROBADA,
                    ano_academico=2023,
                    cuatrimestre=1
                )
            ]
        )
        ingester.estudiantes["EST001"] = est
        
        valido, problemas = ingester.validar_integridad()
        
        assert valido is False
        assert any("9.9.999" in p for p in problemas)

    def test_validar_integridad_falla_plan_distinto(self, ingester, plan_estudio_minimo):
        """
        Vemos si salta el error cuando un pibe dice que es de un plan pero cargamos otro.
        """
        ingester.plan_estudio = plan_estudio_minimo
        
        from kairos.schemas.data_models import EstudianteTrayectoria
        est = EstudianteTrayectoria(
            estudiante_id="EST001",
            codigo_carrera="ING_INF",
            plan_estudio_id="9999", # El plan cargado es "1621"
            ano_ingreso=2023
        )
        ingester.estudiantes["EST001"] = est
        
        valido, problemas = ingester.validar_integridad()
        
        assert valido is False
        assert any("plan 9999 no coincide" in p for p in problemas)

    def test_generar_reporte_errores(self, ingester):
        """
        Vemos si el reporte de errores tira algo coherente cuando hubo pifias.
        """
        ingester.errores_validacion = [
            {"tipo": "EstudianteTrayectoria", "fila": 0, "error": "Algo se rompio", "data": {}}
        ]
        
        reporte = ingester.generar_reporte_errores()
        assert "REPORTE DE ERRORES DE VALIDACION" in reporte
        assert "EstudianteTrayectoria: 1 errores" in reporte
