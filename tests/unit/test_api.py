"""
Tests unitarios para la API de Kairos

Probamos que los endpoints respondan como se debe y no tiren cualquiera.
Usamos TestClient de FastAPI.
"""

import pytest
from fastapi.testclient import TestClient
from kairos.api.main import app

client = TestClient(app)

class TestGeneralAPI:
    """Tests basicos de conectividad."""

    def test_read_root(self):
        """El root tiene que darnos la bienvenida."""
        response = client.get("/")
        assert response.status_code == 200
        assert "¡Bienvenido a Kairos!" in response.json()["mensaje"]

    def test_health_check(self):
        """El health check tiene que estar ok."""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"

class TestOptimizerAPI:
    """Tests de los endpoints del motor."""

    def test_graph_endpoint(self, plan_estudio_minimo):
        """Probamos que el /graph devuelva el grafo visualizable."""
        # Convertimos el plan a dict serializable
        plan_json = plan_estudio_minimo.model_dump(mode="json")
        
        response = client.post("/api/v1/graph", json=plan_json)
        
        assert response.status_code == 200
        data = response.json()
        assert "nodes" in data
        assert "edges" in data
        assert len(data["nodes"]) == 2

    def test_process_endpoint(self, plan_estudio_minimo, estudiante_basico):
        """Probamos el flujo completo de procesamiento via API."""
        payload = {
            "plan": plan_estudio_minimo.model_dump(mode="json"),
            "estudiantes": [estudiante_basico.model_dump(mode="json")],
            "config": {"min_tasa_ocupacion": 0.0} # Forzamos que abra con 1 solo pibe
        }
        
        response = client.post("/api/v1/process", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        assert data["carrera"] == plan_estudio_minimo.nombre_carrera
        assert "prescripciones" in data
        # Con min_tasa 0, deberia abrir la materia siguiente (3.4.070)
        assert data["prescripciones"]["3.4.070"]["decision"] == "ABRIR"

    def test_process_invalid_plan(self):
        """Si le mandamos fruta, tiene que chillar con un 422 (Pydantic validation)."""
        payload = {
            "plan": {"nombre_carrera": "Carrera Invalida"}, # Faltan bocha de campos
            "estudiantes": []
        }
        response = client.post("/api/v1/process", json=payload)
        assert response.status_code == 422
