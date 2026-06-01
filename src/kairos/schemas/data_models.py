"""
Esquemas de datos genericos para Kairos

Define estructuras Pydantic para representar estudiantes, planes de estudio
y recursos disponibles de forma agnostica al sistema transaccional.
"""

from typing import List, Optional, Dict, Set
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field, validator


class EstadoMateria(str, Enum):
    """Estados posibles de una materia en la trayectoria estudiantil"""
    APROBADA = "aprobada"
    REGULAR = "regular"
    INSCRIPTA = "inscripta"
    PENDIENTE = "pendiente"  # Aun no cursada


class RegistroTrayectoria(BaseModel):
    """Registro individual de una materia en la trayectoria de un estudiante"""
    codigo_materia: str
    nombre_materia: str
    estado: EstadoMateria
    ano_academico: int
    cuatrimestre: int
    calificacion: Optional[float] = None  # None si aun no fue evaluada
    fecha_aprobacion: Optional[datetime] = None

    @validator("calificacion")
    def validar_calificacion(cls, v):
        """Frena que la calificacion este entre 0 y 10"""
        if v is not None and not (0 <= v <= 10):
            raise ValueError("Calificacion debe estar entre 0 y 10")
        return v


class EstudianteTrayectoria(BaseModel):
    """
    Representa la trayectoria academica completa de un estudiante.

    Abstraemos los datos personales especificos; solo nos importa
    el historial de cursadas y aprobaciones para el analisis prescriptivo.
    """
    estudiante_id: str
    codigo_carrera: str
    plan_estudio_id: str
    ano_ingreso: int
    turno_preferido: str = "noche"
    registros_trayectoria: List[RegistroTrayectoria] = Field(
        default_factory=list,
        description="Historial de materias cursadas"
    )
    
    class Config:
        use_enum_values = True

    @property
    def materias_aprobadas(self) -> Set[str]:
        """Retorna el conjunto de codigos de materias aprobadas"""
        return {
            r.codigo_materia
            for r in self.registros_trayectoria
            if r.estado == EstadoMateria.APROBADA
        }

    @property
    def materias_cursando(self) -> Set[str]:
        """Retorna materias actualmente en cursada"""
        return {
            r.codigo_materia
            for r in self.registros_trayectoria
            if r.estado in (EstadoMateria.INSCRIPTA, EstadoMateria.REGULAR)
        }

    @property
    def promedio_academico(self) -> Optional[float]:
        """Calcula promedio de materias aprobadas"""
        aprobadas = [
            r for r in self.registros_trayectoria
            if r.estado == EstadoMateria.APROBADA and r.calificacion is not None
        ]
        if not aprobadas:
            return None
        return sum(r.calificacion for r in aprobadas) / len(aprobadas)


class Materia(BaseModel):
    """Representa una asignatura en el plan de estudio"""
    codigo: str
    nombre: str
    ano: int  # Ano del plan donde aparece (1-5)
    cuatrimestre: int  # Cuatrimestre (1-2)
    horas_teoricas: Optional[int] = 0
    horas_practicas: Optional[int] = 0
    creditos: Optional[int] = None
    descripcion: Optional[str] = None
    correlativas_anteriores: List[str] = Field(
        default_factory=list,
        description="Codigos de materias que deben estar aprobadas antes"
    )
    correlativas_posteriores: List[str] = Field(
        default_factory=list,
        description="Codigos de materias que requieren esta como prereq"
    )
    turnos_disponibles: List[str] = Field(
        default_factory=lambda: ["manana", "tarde", "noche"]
    )
    costo_por_turno: Dict[str, float] = Field(
        default_factory=lambda: {"manana": 3000, "tarde": 4000, "noche": 6000}
    )

    @property
    def horas_totales(self) -> int:
        """Total de horas de la materia"""
        return (self.horas_teoricas or 0) + (self.horas_practicas or 0)


class PlanEstudio(BaseModel):
    """
    Representa el plan curricular completo de una carrera.
    
    Define la estructura de anos, cuatrimestres y materias, con sus
    correlatividades. Agnostico a la universidad especifica.
    """
    codigo_plan: str
    nombre_carrera: str
    facultad: Optional[str] = None
    ano_vigencia: int
    duracion_anos: int
    total_creditos: Optional[int] = None
    materias: Dict[str, Materia] = Field(
        description="Diccionario de materias indexed por codigo"
    )

    class Config:
        use_enum_values = True

    @property
    def materias_por_ano(self) -> Dict[int, List[Materia]]:
        """Agrupa materias por ano"""
        agrupadas: Dict[int, List[Materia]] = {}
        for materia in self.materias.values():
            if materia.ano not in agrupadas:
                agrupadas[materia.ano] = []
            agrupadas[materia.ano].append(materia)
        return {k: sorted(v, key=lambda m: m.cuatrimestre) for k, v in agrupadas.items()}

    @property
    def materias_por_cuatrimestre(self) -> Dict[tuple, List[Materia]]:
        """Agrupa materias por (ano, cuatrimestre)"""
        agrupadas: Dict[tuple, List[Materia]] = {}
        for materia in self.materias.values():
            clave = (materia.ano, materia.cuatrimestre)
            if clave not in agrupadas:
                agrupadas[clave] = []
            agrupadas[clave].append(materia)
        return agrupadas

    def obtener_correlativas(self, codigo_materia: str) -> tuple:
        """
        Retorna (correlativas_anteriores, correlativas_posteriores) para una materia
        """
        if codigo_materia not in self.materias:
            return ([], [])
        materia = self.materias[codigo_materia]
        return (materia.correlativas_anteriores, materia.correlativas_posteriores)


class RecursoDisponible(BaseModel):
    """
    Representa recursos academicos disponibles: comisiones, cupos, horarios.
    
    Abstrae la capacidad operativa de la institucion para dictar materias.
    """
    recurso_id: str
    codigo_materia: str
    nombre_materia: str
    ano_academico: int
    cuatrimestre: int
    
    # Capacidad
    cupos_totales: int
    cupos_ocupados: int = 0
    
    # Configuracion
    modalidad: str = "presencial"  # presencial, virtual, hibrida
    horario_inicio: str  # HH:MM
    horario_fin: str    # HH:MM
    dias_semana: List[str] = Field(  # Lunes, Martes, etc
        default_factory=list
    )
    
    # Docente
    docente_id: Optional[str] = None
    docente_nombre: Optional[str] = None
    
    # Costos operativos (para optimizacion)
    costo_operativo_base: Optional[float] = None  # Costo fijo
    costo_por_alumno: Optional[float] = None      # Costo variable

    @property
    def cupos_disponibles(self) -> int:
        """Retorna cupos disponibles"""
        return max(0, self.cupos_totales - self.cupos_ocupados)

    @property
    def tasa_ocupacion(self) -> float:
        """Retorna tasa de ocupacion (0-1)"""
        return self.cupos_ocupados / self.cupos_totales if self.cupos_totales > 0 else 0

    @property
    def costo_total(self) -> Optional[float]:
        """Calcula costo total de operar esta comision"""
        if self.costo_operativo_base is None:
            return None
        costo_var = (
            (self.costo_por_alumno or 0) * self.cupos_ocupados
        )
        return self.costo_operativo_base + costo_var


class ConfiguracionKairos(BaseModel):
    """
    Configuracion global para el motor de optimizacion.

    Los valores por defecto se cargan desde config/kairos_config.json.
    """
    min_tasa_ocupacion: float = 0.6
    max_cupos_por_comision: int = 50
    weight_tasa_graduacion: float = 0.7
    weight_eficiencia_operativa: float = 0.3
    max_comisiones_a_abrir: Optional[int] = None
    anos_estudio: int = 5
    cuatrimestres_por_ano: int = 2

    @validator("min_tasa_ocupacion")
    def validar_tasa(cls, v):
        """Verifica que tasa de ocupacion este en rango [0, 1]"""
        if not (0 <= v <= 1):
            raise ValueError("min_tasa_ocupacion debe estar entre 0 y 1")
        return v

    @validator("weight_tasa_graduacion", "weight_eficiencia_operativa")
    def validar_weights(cls, v):
        """Verifica que los pesos sean probabilidades validas"""
        if not (0 <= v <= 1):
            raise ValueError("Pesos deben estar entre 0 y 1")
        return v
