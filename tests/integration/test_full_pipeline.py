"""
Tests de integracion para el pipeline completo de Kairos

Aca probamos el camino feliz (y no tan feliz) desde que entran los CSV/JSON
crudos hasta que el motor nos dice que materias abrir. Nada de mocks,
probamos la posta.
"""

import pytest
import json
import pandas as pd
from pathlib import Path
from kairos.etl.ingester import DataIngester
from kairos.core.optimizer import KairosOptimizer
from kairos.schemas.data_models import EstadoMateria


class TestFullPipeline:
    """
    Suite de integracion. Simulamos una corrida real del sistema.
    """

    @pytest.fixture
    def setup_data(self, tmp_path):
        """Prepara archivos de prueba reales"""
        # 1. Plan de estudio
        plan_data = {
            "codigo_plan": "1621",
            "nombre_carrera": "Ingenieria en Informatica",
            "ano_vigencia": 2021,
            "duracion_anos": 5,
            "materias": {
                "M1": {"codigo": "M1", "nombre": "Programacion I", "ano": 1, "cuatrimestre": 1},
                "M2": {"codigo": "M2", "nombre": "Programacion II", "ano": 1, "cuatrimestre": 2, "correlativas_anteriores": ["M1"]}
            }
        }
        plan_path = tmp_path / "plan.json"
        with open(plan_path, "w") as f:
            json.dump(plan_data, f)

        # 2. Estudiantes (30 pibes que ya aprobaron M1 y quieren M2)
        est_data = []
        reg_data = []
        for i in range(30):
            est_id = f"EST{i:03d}"
            est_data.append([est_id, "ING_INF", "1621", 2023])
            reg_data.append([est_id, "M1", "Programacion I", "aprobada", 2023, 1, 8.0])

        est_df = pd.DataFrame(est_data, columns=["estudiante_id", "codigo_carrera", "plan_estudio_id", "ano_ingreso"])
        reg_df = pd.DataFrame(reg_data, columns=["estudiante_id", "codigo_materia", "nombre_materia", "estado", "ano_academico", "cuatrimestre", "calificacion"])
        
        est_path = tmp_path / "estudiantes.csv"
        reg_path = tmp_path / "registros.csv"
        est_df.to_csv(est_path, index=False)
        reg_df.to_csv(reg_path, index=False)

        return {
            "plan": plan_path,
            "estudiantes": est_path,
            "registros": reg_path
        }

    def test_pipeline_hasta_prescripcion(self, setup_data):
        """
        Prueba el flujo completo: Carga -> Validacion -> Optimizacion -> Prescripcion.
        """
        # --- ETAPA 1: ETL ---
        ingester = DataIngester()
        ingester.cargar_plan_estudio(setup_data["plan"])
        ingester.cargar_trayectorias_estudiantes(setup_data["estudiantes"])
        ingester.cargar_registros_trayectoria(setup_data["registros"])
        
        valido, problemas = ingester.validar_integridad()
        assert valido is True, f"Bardo en la integridad: {problemas}"
        
        # --- ETAPA 2: Optimizacion ---
        optimizer = KairosOptimizer(ingester.plan_estudio)
        optimizer.agregar_estudiantes(ingester.estudiantes)
        
        demanda = optimizer.analizar_demanda()
        
        # Los 30 pibes deberian querer cursar M2 porque aprobaron M1
        assert demanda["M2"] == 30
        assert "M1" not in demanda # M1 ya la aprobaron todos
        
        # --- ETAPA 3: Prescripcion ---
        # Con 30 pibes y config default (min_tasa=0.6, max_cupos=50 -> min=30), deberia abrir
        prescripciones = optimizer.prescribir_aperturas()
        
        assert prescripciones["M2"]["decision"] == "ABRIR"
        assert len(prescripciones["M2"]["estudiantes_demandantes"]) == 30
        
        print("\nPipeline completado con exito. El motor se la banca.")
