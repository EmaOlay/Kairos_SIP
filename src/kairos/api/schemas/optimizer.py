"""
Esquemas de la API para el Optimizer

Aca definimos que le pedimos al usuario y que le devolvemos.
Usamos los modelos base de kairos pero los tuneamos para la API.
"""

from datetime import datetime
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from kairos.schemas.data_models import (
    PlanEstudio,
    EstudianteTrayectoria,
    ConfiguracionKairos,
    RecursoDisponible,
    Aula,
    Docente,
    HistoricoDictado,
)

class RequestProcesamiento(BaseModel):
    """Lo que necesitamos para arrancar el motor."""
    plan: PlanEstudio
    estudiantes: List[EstudianteTrayectoria]
    recursos: Optional[List[RecursoDisponible]] = []
    aulas: Optional[List[Aula]] = []
    docentes: Optional[List[Docente]] = []
    historico: Optional[List[HistoricoDictado]] = []
    config: Optional[ConfiguracionKairos] = None

class ResponsePrescripcion(BaseModel):
    """El reporte que te tira el motor cuando termina de laburar."""
    carrera: str
    prescripciones: Dict[str, Any]
    cuellos_botella: List[Dict[str, Any]]
    demanda_total: int
    materias_con_demanda: int
    resumen: str
    metricas_operativas: Optional[Dict[str, Any]] = None
    config_usada: Optional[Dict[str, Any]] = None
    # Identificador de la propuesta persistida en el historial. Solo se
    # rellena cuando la corrida fue persistida (endpoint DB-driven).
    propuesta_id: Optional[int] = None


class PropuestaResumen(BaseModel):
    """Entrada del listado de historial: lo justo para listar sin parsear el payload."""
    id: int
    creada_en: datetime
    usuario: str
    codigo_plan: str
    carrera: str
    comisiones_a_abrir: int
    demanda_total: int
    materias_con_demanda: int
    config_usada: Dict[str, Any]


class PropuestaDetalle(BaseModel):
    """Detalle completo de una propuesta historica: misma forma que ResponsePrescripcion + metadatos."""
    id: int
    creada_en: datetime
    usuario: str
    codigo_plan: str
    publicada: bool
    propuesta: ResponsePrescripcion


class ConfigComparativa(BaseModel):
    """Una de las configuraciones a comparar, con etiqueta para el reporte."""
    nombre: str
    config: Optional[ConfiguracionKairos] = None


class RequestReporteComparativo(BaseModel):
    """
    Pide correr el motor con 2-3 configuraciones distintas para compararlas
    lado a lado en la reportería.
    """
    configuraciones: List[ConfigComparativa]


class EscenarioReporte(BaseModel):
    """Resultado resumido de correr el motor con una configuración."""
    nombre: str
    config_usada: Dict[str, Any]
    metricas: Dict[str, Any]


class ResponseReporteComparativo(BaseModel):
    """Comparativa de escenarios para alimentar los gráficos del front."""
    carrera: str
    escenarios: List[EscenarioReporte]


class PublicacionRequest(BaseModel):
    """Request para marcar una propuesta como publicada o privada."""
    publicada: bool
