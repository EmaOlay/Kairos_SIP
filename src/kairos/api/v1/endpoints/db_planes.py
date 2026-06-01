"""
Endpoints DB-driven (RF-010): exponen planes y estudiantes desde la DB
y permiten correr el motor sin que el front mande JSON gigantes.
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from pydantic import ValidationError

from kairos.api.deps import get_db
from kairos.api.schemas.optimizer import ResponsePrescripcion
from kairos.core.optimizer import KairosOptimizer
from kairos.db.models import PlanORM
from kairos.db.repository import EstudianteRepository, PlanRepository
from kairos.schemas.data_models import (
    ConfiguracionKairos,
    EstudianteTrayectoria,
    PlanEstudio,
)

router = APIRouter()


class PlanResumen(BaseModel):
    """Datos basicos de un plan, sin materias."""

    codigo_plan: str
    nombre_carrera: str
    facultad: Optional[str] = None
    ano_vigencia: int
    duracion_anos: int
    total_creditos: Optional[int] = None
    cantidad_materias: int


class ProcessFromDbRequest(BaseModel):
    config: Optional[ConfiguracionKairos] = None


class IngestaEstudiantesResponse(BaseModel):
    persistidos: int
    rechazados: int
    errores: List[str] = []


@router.post("/planes", response_model=PlanResumen, status_code=201)
def ingestar_plan(plan: PlanEstudio, db: Session = Depends(get_db)) -> PlanResumen:
    """
    Ingesta un plan de estudio (idempotente: pisa el existente si el codigo
    ya esta en la DB).
    """
    repo = PlanRepository(db)
    repo.upsert(plan)
    return PlanResumen(
        codigo_plan=plan.codigo_plan,
        nombre_carrera=plan.nombre_carrera,
        facultad=plan.facultad,
        ano_vigencia=plan.ano_vigencia,
        duracion_anos=plan.duracion_anos,
        total_creditos=plan.total_creditos,
        cantidad_materias=len(plan.materias),
    )


@router.post("/estudiantes", response_model=IngestaEstudiantesResponse, status_code=201)
def ingestar_estudiantes(
    estudiantes: List[dict], db: Session = Depends(get_db)
) -> IngestaEstudiantesResponse:
    """
    Ingesta una lista de estudiantes (idempotente por estudiante_id).
    Items invalidos se rechazan individualmente sin abortar el batch.
    """
    repo = EstudianteRepository(db)
    persistidos = 0
    errores: List[str] = []
    for item in estudiantes:
        try:
            est = EstudianteTrayectoria(**item)
        except ValidationError as e:
            errores.append(f"{item.get('estudiante_id', '?')}: {e.error_count()} errores")
            continue
        repo.upsert(est)
        persistidos += 1
    return IngestaEstudiantesResponse(
        persistidos=persistidos,
        rechazados=len(errores),
        errores=errores,
    )


@router.get("/planes", response_model=List[PlanResumen])
def listar_planes(db: Session = Depends(get_db)) -> List[PlanResumen]:
    """Lista todos los planes guardados, con metadata basica."""
    rows = db.execute(select(PlanORM)).scalars().all()
    return [
        PlanResumen(
            codigo_plan=p.codigo_plan,
            nombre_carrera=p.nombre_carrera,
            facultad=p.facultad,
            ano_vigencia=p.ano_vigencia,
            duracion_anos=p.duracion_anos,
            total_creditos=p.total_creditos,
            cantidad_materias=len(p.materias),
        )
        for p in rows
    ]


@router.get("/planes/{codigo_plan}", response_model=PlanEstudio)
def obtener_plan(codigo_plan: str, db: Session = Depends(get_db)) -> PlanEstudio:
    """Devuelve un plan completo (con materias y correlativas)."""
    plan = PlanRepository(db).get(codigo_plan)
    if plan is None:
        raise HTTPException(status_code=404, detail=f"Plan {codigo_plan} no existe")
    return plan


@router.get(
    "/planes/{codigo_plan}/estudiantes",
    response_model=List[EstudianteTrayectoria],
)
def listar_estudiantes(
    codigo_plan: str, db: Session = Depends(get_db)
) -> List[EstudianteTrayectoria]:
    """Devuelve los estudiantes de un plan con todos sus registros de trayectoria."""
    if db.get(PlanORM, codigo_plan) is None:
        raise HTTPException(status_code=404, detail=f"Plan {codigo_plan} no existe")
    return EstudianteRepository(db).list_by_plan(codigo_plan)


@router.post(
    "/planes/{codigo_plan}/process",
    response_model=ResponsePrescripcion,
)
def procesar_desde_db(
    codigo_plan: str,
    request: ProcessFromDbRequest,
    db: Session = Depends(get_db),
) -> ResponsePrescripcion:
    """
    Levanta el plan y los estudiantes de la DB y corre el motor.
    Equivalente a POST /process pero sin que el front mande el JSON entero.
    """
    plan = PlanRepository(db).get(codigo_plan)
    if plan is None:
        raise HTTPException(status_code=404, detail=f"Plan {codigo_plan} no existe")

    estudiantes = EstudianteRepository(db).list_by_plan(codigo_plan)

    optimizer = KairosOptimizer(plan, request.config)
    for est in estudiantes:
        optimizer.agregar_estudiante(est)

    bardo_plan = optimizer.validar_caminos()
    if any("ciclos" in p.lower() for p in bardo_plan):
        raise HTTPException(
            status_code=400,
            detail=f"El plan de estudio tiene ciclos: {bardo_plan}",
        )

    prescripciones = optimizer.prescribir_aperturas()
    demanda = optimizer.analizar_demanda()
    cuellos = optimizer.detectar_cuellos_de_botella()
    resumen = optimizer.reporte_prescriptivo()

    config_efectiva = request.config or ConfiguracionKairos()
    return ResponsePrescripcion(
        carrera=plan.nombre_carrera,
        prescripciones=prescripciones,
        cuellos_botella=cuellos,
        demanda_total=sum(demanda.values()),
        materias_con_demanda=len(demanda),
        resumen=resumen,
        config_usada={
            "weight_tasa_graduacion": config_efectiva.weight_tasa_graduacion,
            "weight_eficiencia_operativa": config_efectiva.weight_eficiencia_operativa,
            "min_tasa_ocupacion": config_efectiva.min_tasa_ocupacion,
            "max_cupos_por_comision": config_efectiva.max_cupos_por_comision,
            "max_comisiones_a_abrir": config_efectiva.max_comisiones_a_abrir,
        },
    )
