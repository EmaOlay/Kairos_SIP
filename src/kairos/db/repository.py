"""
Repositories: persisten/recuperan modelos Pydantic desde la DB.

Cada repository devuelve directamente los Pydantic de kairos.schemas,
asi el motor (KairosOptimizer) los consume sin saber que vinieron de DB.
"""

import json
from typing import Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from kairos.db.models import (
    CorrelativaORM,
    EstudianteORM,
    MateriaORM,
    PlanORM,
    RecursoORM,
    RegistroTrayectoriaORM,
)
from kairos.schemas.data_models import (
    EstadoMateria,
    EstudianteTrayectoria,
    Materia,
    PlanEstudio,
    RecursoDisponible,
    RegistroTrayectoria,
)


def _dump_json(value) -> Optional[str]:
    return json.dumps(value) if value is not None else None


def _load_json(value: Optional[str], default):
    if value is None:
        return default
    try:
        return json.loads(value)
    except (TypeError, ValueError):
        return default


class PlanRepository:
    """Persistencia de planes de estudio + materias + correlativas."""

    def __init__(self, session: Session):
        self.session = session

    def upsert(self, plan: PlanEstudio) -> None:
        """
        Guarda o actualiza un plan completo (idempotente).
        Si ya existia, lo borra y lo regraba: simple y suficiente para el MVP.
        """
        existente = self.session.get(PlanORM, plan.codigo_plan)
        if existente is not None:
            self.session.delete(existente)
            self.session.flush()

        plan_orm = PlanORM(
            codigo_plan=plan.codigo_plan,
            nombre_carrera=plan.nombre_carrera,
            facultad=plan.facultad,
            ano_vigencia=plan.ano_vigencia,
            duracion_anos=plan.duracion_anos,
            total_creditos=plan.total_creditos,
        )
        self.session.add(plan_orm)
        self.session.flush()

        for materia in plan.materias.values():
            materia_orm = MateriaORM(
                codigo=materia.codigo,
                plan_codigo=plan.codigo_plan,
                nombre=materia.nombre,
                ano=materia.ano,
                cuatrimestre=materia.cuatrimestre,
                horas_teoricas=materia.horas_teoricas,
                horas_practicas=materia.horas_practicas,
                creditos=materia.creditos,
                descripcion=materia.descripcion,
                turnos_disponibles_json=_dump_json(materia.turnos_disponibles),
                costo_por_turno_json=_dump_json(materia.costo_por_turno),
            )
            self.session.add(materia_orm)
        self.session.flush()

        for materia in plan.materias.values():
            for prereq in materia.correlativas_anteriores:
                if prereq not in plan.materias:
                    continue
                self.session.add(
                    CorrelativaORM(
                        materia_codigo=materia.codigo,
                        prerequisito_codigo=prereq,
                    )
                )
        self.session.commit()

    def get(self, codigo_plan: str) -> Optional[PlanEstudio]:
        """Lee un plan completo y lo devuelve como Pydantic listo para el motor."""
        stmt = (
            select(PlanORM)
            .where(PlanORM.codigo_plan == codigo_plan)
            .options(
                selectinload(PlanORM.materias).selectinload(
                    MateriaORM.correlativas_anteriores
                )
            )
        )
        plan_orm = self.session.execute(stmt).scalar_one_or_none()
        if plan_orm is None:
            return None

        materias: Dict[str, Materia] = {}
        for m in plan_orm.materias:
            materias[m.codigo] = Materia(
                codigo=m.codigo,
                nombre=m.nombre,
                ano=m.ano,
                cuatrimestre=m.cuatrimestre,
                horas_teoricas=m.horas_teoricas or 0,
                horas_practicas=m.horas_practicas or 0,
                creditos=m.creditos,
                descripcion=m.descripcion,
                correlativas_anteriores=[
                    c.prerequisito_codigo for c in m.correlativas_anteriores
                ],
                turnos_disponibles=_load_json(
                    m.turnos_disponibles_json, ["manana", "tarde", "noche"]
                ),
                costo_por_turno=_load_json(
                    m.costo_por_turno_json,
                    {"manana": 3000, "tarde": 4000, "noche": 6000},
                ),
            )

        return PlanEstudio(
            codigo_plan=plan_orm.codigo_plan,
            nombre_carrera=plan_orm.nombre_carrera,
            facultad=plan_orm.facultad,
            ano_vigencia=plan_orm.ano_vigencia,
            duracion_anos=plan_orm.duracion_anos,
            total_creditos=plan_orm.total_creditos,
            materias=materias,
        )


class EstudianteRepository:
    """Persistencia de estudiantes y sus registros de trayectoria."""

    def __init__(self, session: Session):
        self.session = session

    def upsert(self, estudiante: EstudianteTrayectoria) -> None:
        existente = self.session.get(EstudianteORM, estudiante.estudiante_id)
        if existente is not None:
            self.session.delete(existente)
            self.session.flush()

        est_orm = EstudianteORM(
            estudiante_id=estudiante.estudiante_id,
            codigo_carrera=estudiante.codigo_carrera,
            plan_estudio_id=estudiante.plan_estudio_id,
            ano_ingreso=estudiante.ano_ingreso,
            turno_preferido=estudiante.turno_preferido,
        )
        self.session.add(est_orm)
        self.session.flush()

        for r in estudiante.registros_trayectoria:
            estado = r.estado if isinstance(r.estado, str) else r.estado.value
            self.session.add(
                RegistroTrayectoriaORM(
                    estudiante_id=estudiante.estudiante_id,
                    codigo_materia=r.codigo_materia,
                    nombre_materia=r.nombre_materia,
                    estado=estado,
                    ano_academico=r.ano_academico,
                    cuatrimestre=r.cuatrimestre,
                    calificacion=r.calificacion,
                    fecha_aprobacion=r.fecha_aprobacion,
                )
            )
        self.session.commit()

    def list_by_plan(self, plan_estudio_id: str) -> List[EstudianteTrayectoria]:
        stmt = (
            select(EstudianteORM)
            .where(EstudianteORM.plan_estudio_id == plan_estudio_id)
            .options(selectinload(EstudianteORM.registros))
        )
        rows = self.session.execute(stmt).scalars().all()
        return [self._to_pydantic(e) for e in rows]

    def get(self, estudiante_id: str) -> Optional[EstudianteTrayectoria]:
        stmt = (
            select(EstudianteORM)
            .where(EstudianteORM.estudiante_id == estudiante_id)
            .options(selectinload(EstudianteORM.registros))
        )
        e = self.session.execute(stmt).scalar_one_or_none()
        return self._to_pydantic(e) if e else None

    @staticmethod
    def _to_pydantic(e: EstudianteORM) -> EstudianteTrayectoria:
        registros = [
            RegistroTrayectoria(
                codigo_materia=r.codigo_materia,
                nombre_materia=r.nombre_materia,
                estado=EstadoMateria(r.estado),
                ano_academico=r.ano_academico,
                cuatrimestre=r.cuatrimestre,
                calificacion=r.calificacion,
                fecha_aprobacion=r.fecha_aprobacion,
            )
            for r in e.registros
        ]
        return EstudianteTrayectoria(
            estudiante_id=e.estudiante_id,
            codigo_carrera=e.codigo_carrera,
            plan_estudio_id=e.plan_estudio_id,
            ano_ingreso=e.ano_ingreso,
            turno_preferido=e.turno_preferido,
            registros_trayectoria=registros,
        )


class RecursoRepository:
    """Persistencia de recursos (comisiones)."""

    def __init__(self, session: Session):
        self.session = session

    def upsert(self, recurso: RecursoDisponible) -> None:
        existente = self.session.get(RecursoORM, recurso.recurso_id)
        if existente is not None:
            self.session.delete(existente)
            self.session.flush()

        self.session.add(
            RecursoORM(
                recurso_id=recurso.recurso_id,
                codigo_materia=recurso.codigo_materia,
                nombre_materia=recurso.nombre_materia,
                ano_academico=recurso.ano_academico,
                cuatrimestre=recurso.cuatrimestre,
                cupos_totales=recurso.cupos_totales,
                cupos_ocupados=recurso.cupos_ocupados,
                modalidad=recurso.modalidad,
                horario_inicio=recurso.horario_inicio,
                horario_fin=recurso.horario_fin,
                dias_semana=",".join(recurso.dias_semana) if recurso.dias_semana else None,
                docente_id=recurso.docente_id,
                docente_nombre=recurso.docente_nombre,
                costo_operativo_base=recurso.costo_operativo_base,
                costo_por_alumno=recurso.costo_por_alumno,
            )
        )
        self.session.commit()

    def list_all(self) -> List[RecursoDisponible]:
        rows = self.session.execute(select(RecursoORM)).scalars().all()
        return [self._to_pydantic(r) for r in rows]

    @staticmethod
    def _to_pydantic(r: RecursoORM) -> RecursoDisponible:
        dias = r.dias_semana.split(",") if r.dias_semana else []
        return RecursoDisponible(
            recurso_id=r.recurso_id,
            codigo_materia=r.codigo_materia,
            nombre_materia=r.nombre_materia,
            ano_academico=r.ano_academico,
            cuatrimestre=r.cuatrimestre,
            cupos_totales=r.cupos_totales,
            cupos_ocupados=r.cupos_ocupados,
            modalidad=r.modalidad,
            horario_inicio=r.horario_inicio,
            horario_fin=r.horario_fin,
            dias_semana=dias,
            docente_id=r.docente_id,
            docente_nombre=r.docente_nombre,
            costo_operativo_base=r.costo_operativo_base,
            costo_por_alumno=r.costo_por_alumno,
        )
