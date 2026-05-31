"""
Configuracion compartida para tests (fixtures)
"""

import pytest
from datetime import datetime
from kairos.schemas.data_models import (
    EstadoMateria,
    RegistroTrayectoria,
    EstudianteTrayectoria,
    Materia,
    PlanEstudio,
    RecursoDisponible,
)


@pytest.fixture
def registro_trayectoria_aprobada():
    """Fixture: registro de una materia aprobada"""
    return RegistroTrayectoria(
        codigo_materia="3.4.069",
        nombre_materia="Fundamentos de Informatica",
        estado=EstadoMateria.APROBADA,
        ano_academico=2023,
        cuatrimestre=1,
        calificacion=8.5,
        fecha_aprobacion=datetime(2023, 6, 30),
    )


@pytest.fixture
def registro_trayectoria_inscripta():
    """Fixture: registro de una materia inscripta"""
    return RegistroTrayectoria(
        codigo_materia="3.4.070",
        nombre_materia="Estructura de Datos",
        estado=EstadoMateria.INSCRIPTA,
        ano_academico=2024,
        cuatrimestre=1,
        calificacion=None,
    )


@pytest.fixture
def estudiante_basico(registro_trayectoria_aprobada, registro_trayectoria_inscripta):
    """Fixture: estudiante con registros"""
    return EstudianteTrayectoria(
        estudiante_id="EST001",
        codigo_carrera="ING_INF",
        plan_estudio_id="1621",
        ano_ingreso=2023,
        registros_trayectoria=[registro_trayectoria_aprobada, registro_trayectoria_inscripta],
    )


@pytest.fixture
def materia_basica():
    """Fixture: materia sin correlativas"""
    return Materia(
        codigo="3.4.069",
        nombre="Fundamentos de Informatica",
        ano=1,
        cuatrimestre=1,
        horas_teoricas=30,
        horas_practicas=30,
        creditos=6,
    )


@pytest.fixture
def materia_con_correlativas():
    """Fixture: materia con correlativas"""
    return Materia(
        codigo="3.4.070",
        nombre="Estructura de Datos",
        ano=1,
        cuatrimestre=2,
        horas_teoricas=40,
        horas_practicas=20,
        creditos=8,
        correlativas_anteriores=["3.4.069"],
    )


@pytest.fixture
def plan_estudio_minimo(materia_basica, materia_con_correlativas):
    """Fixture: plan de estudio minimo (2 materias)"""
    return PlanEstudio(
        codigo_plan="1621",
        nombre_carrera="Ingenieria en Informatica",
        facultad="Ingenieria",
        ano_vigencia=2021,
        duracion_anos=5,
        total_creditos=150,
        materias={
            "3.4.069": materia_basica,
            "3.4.070": materia_con_correlativas,
        },
    )


@pytest.fixture
def recurso_disponible_basico():
    """Fixture: recurso disponible (comision)"""
    return RecursoDisponible(
        recurso_id="COM001",
        codigo_materia="3.4.069",
        nombre_materia="Fundamentos de Informatica",
        ano_academico=2025,
        cuatrimestre=1,
        cupos_totales=50,
        cupos_ocupados=30,
        modalidad="presencial",
        horario_inicio="09:00",
        horario_fin="12:00",
        dias_semana=["Lunes", "Miercoles"],
        docente_id="DOC001",
        docente_nombre="Ing. Juan Perez",
        costo_operativo_base=1000.0,
        costo_por_alumno=50.0,
    )


@pytest.fixture
def recurso_disponible_lleno():
    """Fixture: recurso con cupos completos"""
    return RecursoDisponible(
        recurso_id="COM002",
        codigo_materia="3.4.070",
        nombre_materia="Estructura de Datos",
        ano_academico=2025,
        cuatrimestre=1,
        cupos_totales=40,
        cupos_ocupados=40,
        modalidad="presencial",
        horario_inicio="14:00",
        horario_fin="17:00",
        dias_semana=["Martes", "Jueves"],
    )
