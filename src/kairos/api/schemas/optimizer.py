"""
Esquemas de la API para el Optimizer

Aca definimos que le pedimos al usuario y que le devolvemos.
Usamos los modelos base de kairos pero los tuneamos para la API.
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from kairos.schemas.data_models import (
    PlanEstudio, 
    EstudianteTrayectoria, 
    ConfiguracionKairos,
    RecursoDisponible
)

class RequestProcesamiento(BaseModel):
    """Lo que necesitamos para arrancar el motor."""
    plan: PlanEstudio
    estudiantes: List[EstudianteTrayectoria]
    recursos: Optional[List[RecursoDisponible]] = []
    config: Optional[ConfiguracionKairos] = None

class ResponsePrescripcion(BaseModel):
    """El reporte que te tira el motor cuando termina de laburar."""
    carrera: str
    prescripciones: Dict[str, Any]
    cuellos_botella: List[Dict[str, Any]]
    demanda_total: int
    materias_con_demanda: int
    resumen: str
