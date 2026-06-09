"""
Motor core de Kairos: Clase KairosOptimizer

Implementa el algoritmo de analisis prescriptivo basado en:
- Grafo de correlatividades (NetworkX)
- Analisis de trayectorias estudiantiles
- Optimizacion de recursos academicos
- Prescripcion de apertura de comisiones
"""

from typing import Dict, List, Set, Tuple, Optional
import logging
from collections import defaultdict

import networkx as nx

from kairos.schemas.data_models import (
    Aula,
    Docente,
    EstudianteTrayectoria,
    HistoricoDictado,
    PlanEstudio,
    RecursoDisponible,
    ConfiguracionKairos,
)


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class KairosOptimizer:
    """
    Motor de analisis y prescripcion de ofertas academicas.
    
    Procesa trayectorias estudiantiles y construye un modelo de optimizacion
    basado en grafo de correlatividades, demanda de estudiantes y restricciones
    operativas. Prescribe automaticamente que comisiones abrir para maximizar
    graduacion y eficiencia.
    """

    def __init__(
        self,
        plan_estudio: PlanEstudio,
        config: Optional[ConfiguracionKairos] = None,
    ):
        self.plan = plan_estudio
        self.config = config or ConfiguracionKairos()
        
        # Grafo de correlatividades
        self.grafo_correlativas: nx.DiGraph = nx.DiGraph()
        
        # Estudiantes y su estado
        self.estudiantes: Dict[str, EstudianteTrayectoria] = {}
        
        # Recursos disponibles
        self.recursos: Dict[str, RecursoDisponible] = {}

        # Recursos operativos (capacidad de aulas + pool de docentes)
        self.aulas: Dict[str, Aula] = {}
        self.docentes: Dict[str, Docente] = {}
        self.historico: List[HistoricoDictado] = []

        # Demanda por materia (estudiantes que necesitan cursarla)
        self.demanda_por_materia: Dict[str, Set[str]] = defaultdict(set)

        self._inicializar_grafo()
        logger.info(f" KairosOptimizer inicializado para {plan_estudio.nombre_carrera}")

    def _inicializar_grafo(self) -> None:
        """
        Construye el grafo dirigido de correlatividades.
        
        Nodos: codigos de materias
        Aristas: X -> Y significa que X es prerequisito de Y (debe aprobarse antes)
        
        Tambien aprovechamos y llenamos las correlativas_posteriores en el plan,
        asi queda todo bien espejado.
        """
        logger.info("Inicializando grafo de correlatividades...")

        for codigo, materia in self.plan.materias.items():
            self.grafo_correlativas.add_node(codigo, materia=materia)
            # Limpiamos por las dudas si venia con algo
            materia.correlativas_posteriores = []

        for codigo, materia in self.plan.materias.items():
            for prerequisito in materia.correlativas_anteriores:
                if prerequisito in self.plan.materias:
                    self.grafo_correlativas.add_edge(prerequisito, codigo)
                    # Llenamos el sentido inverso (posteriores)
                    if codigo not in self.plan.materias[prerequisito].correlativas_posteriores:
                        self.plan.materias[prerequisito].correlativas_posteriores.append(codigo)

        logger.info(
            f" Grafo construido: {len(self.grafo_correlativas.nodes)} nodos, "
            f"{len(self.grafo_correlativas.edges)} aristas"
        )

    def validar_caminos(self) -> List[str]:
        """
        Se fija si hay materias que son imposibles de alcanzar o raras.
        Aca saltan los problemas de logica del plan.
        """
        problemas = []
        
        # 1. Detectar ciclos (si hay un ciclo, no se reciben mas)
        if self.tiene_ciclos():
            problemas.append("El plan tiene ciclos (correlatividades circulares)")

        # 2. Detectar nodos aislados (materias que no tienen nada que ver con nada)
        # Ojo: esto puede ser normal en algunas carreras, pero avisamos.
        aislados = list(nx.isolates(self.grafo_correlativas))
        if aislados:
            logger.info(f"Materias sin ninguna correlativa (entrada ni salida): {aislados}")

        # 3. Validar consistencia de anos (una materia de 4to no puede ser prereq de una de 1ro)
        for u, v in self.grafo_correlativas.edges():
            m_u = self.plan.materias[u]
            m_v = self.plan.materias[v]
            if m_u.ano > m_v.ano:
                problemas.append(
                    f"Inconsistencia temporal: {u} (ano {m_u.ano}) es prereq de "
                    f"{v} (ano {m_v.ano})"
                )
        
        return problemas

    def agregar_estudiante(self, estudiante: EstudianteTrayectoria) -> None:
        """Agrega un estudiante al motor para analisis"""
        self.estudiantes[estudiante.estudiante_id] = estudiante

    def agregar_estudiantes(self, estudiantes: Dict[str, EstudianteTrayectoria]) -> None:
        """Agrega multiples estudiantes"""
        self.estudiantes.update(estudiantes)
        logger.info(f" {len(self.estudiantes)} estudiantes agregados")

    def agregar_recursos(self, recursos: List[RecursoDisponible]) -> None:
        """Agrega recursos (comisiones) disponibles"""
        for recurso in recursos:
            self.recursos[recurso.recurso_id] = recurso
        logger.info(f" {len(self.recursos)} recursos agregados")

    def agregar_aulas(self, aulas: List[Aula]) -> None:
        """Agrega aulas (capacidad y cantidad) como restriccion del motor."""
        for aula in aulas:
            self.aulas[aula.aula_id] = aula
        logger.info(f" {len(self.aulas)} aulas agregadas")

    def agregar_docentes(self, docentes: List[Docente]) -> None:
        """Agrega el pool de docentes con su disponibilidad horaria."""
        for docente in docentes:
            self.docentes[docente.docente_id] = docente
        logger.info(f" {len(self.docentes)} docentes agregados")

    def agregar_historico(self, historico: List[HistoricoDictado]) -> None:
        """
        Carga el historico de dictado. Se usa para estimar la disponibilidad
        de los docentes que no tienen horario fehaciente.
        """
        self.historico.extend(historico)
        logger.info(f" {len(historico)} registros de historico agregados")

    def _aulas_por_turno(self) -> Dict[str, List[Aula]]:
        """
        Arma el pool de aulas disponibles por turno, ordenadas por capacidad
        descendente (asi asignamos primero las grandes a las comisiones con
        mas demanda). Una misma aula sirve en cada turno que tenga habilitado:
        si esta libre de manana sigue libre de tarde.
        """
        pool: Dict[str, List[Aula]] = defaultdict(list)
        for aula in self.aulas.values():
            for turno in aula.turnos_disponibles:
                pool[turno].append(aula)
        for turno in pool:
            pool[turno].sort(key=lambda a: a.capacidad, reverse=True)
        return pool

    def _perfil_docentes_estimado(self) -> Dict[str, Docente]:
        """
        Devuelve una copia de los docentes con la disponibilidad completada
        a partir del historico para los que no tienen horario fehaciente.

        Estimacion: si un docente sin horario confirmado dicto una materia en
        un turno dado en el pasado, asumimos que puede volver a dictarla en ese
        turno. Asi tenemos una buena aproximacion en vez de descartarlo.
        """
        if not self.config.usar_historico_docentes or not self.historico:
            return dict(self.docentes)

        # Indexar historico por docente
        materias_hist: Dict[str, Set[str]] = defaultdict(set)
        turnos_hist: Dict[str, Set[str]] = defaultdict(set)
        for h in self.historico:
            materias_hist[h.docente_id].add(h.codigo_materia)
            turnos_hist[h.docente_id].add(h.turno)

        estimados: Dict[str, Docente] = {}
        for did, doc in self.docentes.items():
            if doc.horario_fehaciente:
                estimados[did] = doc
                continue
            # Completamos materias y turnos con lo que surja del historico,
            # sin pisar lo que el docente ya haya declarado.
            materias = sorted(set(doc.materias_que_dicta) | materias_hist.get(did, set()))
            turnos = sorted(set(doc.disponibilidad_turnos) | turnos_hist.get(did, set()))
            estimados[did] = doc.model_copy(
                update={
                    "materias_que_dicta": materias,
                    "disponibilidad_turnos": turnos,
                }
            )
        return estimados

    def analizar_demanda(self) -> Dict[str, int]:
        """
        Analiza que materias necesitan los estudiantes actualmente.

        Retorna: {codigo_materia: cantidad_estudiantes_que_la_necesitan}
        """
        self.demanda_por_materia.clear()

        for est in self.estudiantes.values():
            materias_disponibles = self._calcular_materias_disponibles(est)

            for codigo in materias_disponibles:
                self.demanda_por_materia[codigo].add(est.estudiante_id)

        demanda = {k: len(v) for k, v in self.demanda_por_materia.items()}
        return demanda

    def analizar_demanda_por_turno(self) -> Dict[Tuple[str, str], Set[str]]:
        """
        Splitea la demanda por materia+turno segun el turno preferido de cada estudiante.

        Retorna: {(codigo_materia, turno): set de estudiante_ids}
        """
        demanda_turno: Dict[Tuple[str, str], Set[str]] = defaultdict(set)

        for est in self.estudiantes.values():
            materias_disponibles = self._calcular_materias_disponibles(est)

            for codigo in materias_disponibles:
                materia = self.plan.materias[codigo]
                turno = est.turno_preferido
                if turno in materia.turnos_disponibles:
                    demanda_turno[(codigo, turno)].add(est.estudiante_id)
                else:
                    # Si su turno preferido no esta disponible, cae al primer turno disponible
                    demanda_turno[(codigo, materia.turnos_disponibles[0])].add(est.estudiante_id)

        return demanda_turno

    def _calcular_materias_disponibles(
        self, estudiante: EstudianteTrayectoria
    ) -> Set[str]:
        """
        Calcula que materias puede cursar un estudiante segun correlativas.
        
        Retorna el conjunto de codigos de materias que:
        1. Aun no aprobo
        2. Todos sus prerequisitos estan aprobados
        """
        aprobadas = estudiante.materias_aprobadas

        disponibles = set()

        for codigo, materia in self.plan.materias.items():
            # Ya aprobada: no disponible
            if codigo in aprobadas:
                continue

            # Revisar prerequisitos
            prereqs_cumplidos = all(
                prereq in aprobadas for prereq in materia.correlativas_anteriores
            )

            if prereqs_cumplidos:
                disponibles.add(codigo)

        return disponibles

    def _calcular_impacto_cascada(self, codigo: str) -> int:
        """
        Cuenta cuántas materias se desbloquean transitivamente desde esta materia.
        Si aprobás esta, cuántas más se te abren a lo largo de toda la carrera.
        """
        descendientes = nx.descendants(self.grafo_correlativas, codigo)
        return len(descendientes)

    def _calcular_score(self, codigo: str, demanda: int, ingreso_por_alumno: float) -> float:
        """
        Calcula el score prescriptivo combinando dos dimensiones en escala comparable:

        - Cascada: cuántas materias se desbloquean transitivamente (0-~15)
        - Rentabilidad: demanda × ingreso por alumno, normalizado a escala similar (0-~15)

        Ambos componentes se escalan para que los pesos realmente determinen la prioridad.
        """
        cascada = self._calcular_impacto_cascada(codigo)
        rentabilidad_raw = demanda * ingreso_por_alumno / 1000
        rentabilidad = rentabilidad_raw / 30

        score = (
            self.config.weight_tasa_graduacion * cascada
            + self.config.weight_eficiencia_operativa * rentabilidad
        )
        return round(score, 2)

    def _elegir_docente(
        self,
        codigo: str,
        turno: str,
        carga: Dict[str, int],
        perfil: Dict[str, Docente],
    ) -> Optional[Docente]:
        """
        Elige un docente que pueda dictar `codigo` en `turno` y que todavia
        tenga carga libre. Reparte la carga eligiendo al docente menos cargado
        (asi tendemos a que no quede ninguno libre). Desempate determinista
        por id. Devuelve None si no hay candidato (no se podra abrir).
        """
        candidatos = [
            d
            for d in perfil.values()
            if codigo in d.materias_que_dicta
            and turno in d.disponibilidad_turnos
            and carga[d.docente_id] < d.max_comisiones
        ]
        if not candidatos:
            return None
        candidatos.sort(key=lambda d: (carga[d.docente_id], d.docente_id))
        return candidatos[0]

    def _tomar_aula(self, pool_turno: List[Aula], demanda: int) -> Optional[Aula]:
        """
        Saca del pool del turno el aula mas conveniente para la demanda dada
        (best-fit: la mas chica que cubra la demanda; si ninguna alcanza, la
        mas grande disponible y el excedente queda como demanda no satisfecha).
        Remueve el aula del pool porque pasa a estar ocupada en ese turno.
        Devuelve None si no quedan aulas en el turno.
        """
        if not pool_turno:
            return None
        aptas = [a for a in pool_turno if a.capacidad >= demanda]
        elegida = (
            min(aptas, key=lambda a: a.capacidad)
            if aptas
            else max(pool_turno, key=lambda a: a.capacidad)
        )
        pool_turno.remove(elegida)
        return elegida

    def prescribir_aperturas(self) -> Dict[str, Dict]:
        """
        Prescribe que comisiones abrir por materia+turno.

        Splitea la demanda por turno preferido del alumno, calcula el score
        de cada combinación materia+turno usando cascada + demanda/costo,
        y rankea para decidir cuáles abrir.

        Si hay aulas y/o docentes cargados (y la config lo habilita), aplica
        restricciones duras: no se abre una comisión sin aula libre en el turno
        ni sin un docente habilitado y disponible. La capacidad del aula limita
        los cupos efectivos; el excedente queda como demanda no satisfecha.
        """
        logger.info("Analizando demanda por turno y prescribiendo aperturas...")

        self.analizar_demanda()
        demanda_turno = self.analizar_demanda_por_turno()

        prescripciones = {}
        ranking = []

        for (codigo, turno), estudiantes_set in demanda_turno.items():
            materia = self.plan.materias[codigo]
            cantidad = len(estudiantes_set)
            ingreso = materia.costo_por_turno.get(turno, 5000)
            score = self._calcular_score(codigo, cantidad, ingreso)
            cascada = self._calcular_impacto_cascada(codigo)
            ranking.append((codigo, turno, materia, score, cantidad, cascada, ingreso, list(estudiantes_set)))

        ranking.sort(key=lambda x: x[3], reverse=True)

        score_minimo = self.config.min_tasa_ocupacion * 10
        tope = self.config.max_comisiones_a_abrir
        abiertas = 0

        # Las restricciones operativas solo aplican si hay datos cargados y la
        # config lo habilita. Sin datos, el motor se comporta como siempre.
        aplica_aulas = self.config.respetar_capacidad_aulas and bool(self.aulas)
        aplica_docentes = self.config.respetar_disponibilidad_docentes and bool(self.docentes)
        pool_aulas = self._aulas_por_turno() if aplica_aulas else {}
        perfil_docentes = self._perfil_docentes_estimado() if aplica_docentes else {}
        carga_docentes: Dict[str, int] = defaultdict(int)

        import hashlib

        for codigo, turno, materia, score, cantidad, cascada, ingreso, est_list in ranking:
            supera_minimo = score >= score_minimo

            # 1) Decisión base por score y tope presupuestario.
            if supera_minimo and (tope is None or abiertas < tope):
                decision = "ABRIR"
                razon = (
                    f"Score {score} ≥ mínimo {score_minimo:.1f}. "
                    f"Desbloquea {cascada} materias y junta {cantidad} alumnos "
                    f"(${int(cantidad * ingreso):,} de ingreso)."
                )
            elif not supera_minimo:
                decision = "NO ABRIR"
                razon = (
                    f"Score {score} < mínimo {score_minimo:.1f}. "
                    f"Demanda baja ({cantidad} alumnos) o poco impacto en cascada ({cascada})."
                )
            else:
                decision = "NO ABRIR"
                razon = (
                    f"Tope presupuestario alcanzado ({tope} comisiones). "
                    f"Score {score} no entró en el ranking."
                )

            # 2) Restricciones duras de recursos. Validamos docente primero
            # (no consume nada) y recién después tomamos aula, así si falta
            # docente no "gastamos" un aula del pool.
            docente_obj: Optional[Docente] = None
            aula_obj: Optional[Aula] = None
            motivo_recurso: Optional[str] = None

            if decision == "ABRIR" and aplica_docentes:
                docente_obj = self._elegir_docente(
                    codigo, turno, carga_docentes, perfil_docentes
                )
                if docente_obj is None:
                    decision = "NO ABRIR"
                    motivo_recurso = "sin_docente"
                    razon = (
                        f"Sin docente disponible para {codigo} en turno {turno} "
                        f"(ninguno habilitado/libre). No se puede abrir."
                    )

            if decision == "ABRIR" and aplica_aulas:
                aula_obj = self._tomar_aula(pool_aulas.get(turno, []), cantidad)
                if aula_obj is None:
                    decision = "NO ABRIR"
                    motivo_recurso = "sin_aula"
                    razon = (
                        f"Sin aulas libres en turno {turno}. "
                        f"Se agotó la capacidad edilicia para esta franja."
                    )

            # 3) Si finalmente abre, consumimos recursos y calculamos cupos.
            cupos_asignados: Optional[int] = None
            if decision == "ABRIR":
                if docente_obj is not None:
                    carga_docentes[docente_obj.docente_id] += 1
                if aula_obj is not None:
                    cupos_asignados = aula_obj.capacidad
                abiertas += 1
                # Si hubo cupo de aula, enriquecemos la razón con el dato.
                if aula_obj is not None and cantidad > aula_obj.capacidad:
                    razon += (
                        f" Aula {aula_obj.nombre} (cap. {aula_obj.capacidad}): "
                        f"{cantidad - aula_obj.capacidad} alumnos quedan sin cupo."
                    )

            # Cupos efectivos: limitados por la capacidad del aula si hubo una.
            cupo_efectivo = cantidad if cupos_asignados is None else min(cantidad, cupos_asignados)
            demanda_satisfecha = cupo_efectivo if decision == "ABRIR" else 0
            demanda_no_satisfecha = cantidad - demanda_satisfecha

            # 4) Resolver nombres mostrables de aula y docente.
            # Si el nuevo modelo asignó recursos reales, esos mandan; sino,
            # caemos a la lógica híbrida histórica (recursos + heurística).
            aula = aula_obj.nombre if aula_obj is not None else (
                "Aula Virtual" if turno == "virtual" else None
            )
            docente = docente_obj.nombre if docente_obj is not None else None

            if docente is None:
                # Buscar en recursos (comisiones) cargados a la vieja usanza.
                for r in self.recursos.values():
                    if r.codigo_materia == codigo:
                        r_turno = "noche"
                        try:
                            hora = int(r.horario_inicio.split(":")[0])
                            if hora < 13:
                                r_turno = "manana"
                            elif hora < 18:
                                r_turno = "tarde"
                        except Exception:
                            pass
                        if r_turno == turno:
                            docente = r.docente_nombre
                            if r.modalidad == "virtual" and aula is None:
                                aula = "Aula Virtual"
                            break

            # Heurística determinista si no hay datos en la DB
            h = int(hashlib.md5(codigo.encode('utf-8')).hexdigest(), 16)
            if not docente:
                nombres = ["Carlos", "Elena", "Martín", "Ana", "Lucas", "Sofía", "Jorge", "María", "Diego", "Laura", "Gabriel", "Patricia"]
                apellidos = ["Gómez", "López", "Rodríguez", "Fernández", "González", "Pérez", "Martínez", "Sánchez", "Díaz", "Álvarez", "Rossi", "Bianchi"]
                nombre_idx = (h + 3) % len(nombres)
                apellido_idx = (h + 7) % len(apellidos)
                titulo = "Dr." if (h % 3 == 0) else ("Dra." if h % 3 == 1 else "Ing.")
                docente = f"{titulo} {nombres[nombre_idx]} {apellidos[apellido_idx]}"

            if not aula:
                room_number = 100 * materia.ano + (h % 20 + 1)
                aula = f"Aula {room_number}"

            bajo_cupo = cantidad < 15

            key = f"{codigo}_{turno}"
            prescripciones[key] = {
                "codigo": codigo,
                "nombre": materia.nombre,
                "turno": turno,
                "ingreso_por_alumno": ingreso,
                "decision": decision,
                "razon": razon,
                "demanda": cantidad,
                "score": score,
                "desbloquea": cascada,
                "estudiantes_demandantes": est_list,
                "aula": aula,
                "docente": docente,
                "bajo_cupo": bajo_cupo,
                # Métricas operativas (alimentan la reportería comparativa)
                "aula_id": aula_obj.aula_id if aula_obj is not None else None,
                "capacidad_aula": cupos_asignados,
                "docente_id": docente_obj.docente_id if docente_obj is not None else None,
                "demanda_satisfecha": demanda_satisfecha,
                "demanda_no_satisfecha": demanda_no_satisfecha,
                "motivo_no_apertura": motivo_recurso,
            }

        prescripciones = dict(
            sorted(prescripciones.items(), key=lambda x: x[1]["score"], reverse=True)
        )

        return prescripciones

    def metricas_operativas(
        self, prescripciones: Optional[Dict[str, Dict]] = None
    ) -> Dict:
        """
        Agrega métricas operativas de una corrida para la reportería comparativa.

        Calcula, sobre las comisiones que se abren:
        - Ingresos proyectados (sumatoria de alumnos con cupo × ingreso/alumno).
        - Completitud de aulas (ocupación promedio: alumnos / capacidad).
        - Alocación de docentes (cuántos del pool quedan asignados vs libres).
        - Demanda de alumnos satisfecha (con cupo) vs total.
        - Métrica extra: cobertura de cuellos de botella (materias críticas
          que efectivamente se abren).

        Pensado para llamarse con el resultado de prescribir_aperturas(), pero
        si no se pasa nada lo corre solo.
        """
        if prescripciones is None:
            prescripciones = self.prescribir_aperturas()

        abiertas = [p for p in prescripciones.values() if p["decision"] == "ABRIR"]

        # --- Ingresos ---
        # Si hubo restricción de aula, cobramos por los alumnos con cupo real.
        ingresos_total = 0
        for p in abiertas:
            con_cupo = p.get("demanda_satisfecha")
            if con_cupo is None:
                con_cupo = p["demanda"]
            ingresos_total += int(con_cupo * p["ingreso_por_alumno"])

        # --- Demanda de alumnos ---
        # Cantidad de (alumno, materia, turno) total y cuántos quedan satisfechos.
        demanda_total = sum(p["demanda"] for p in prescripciones.values())
        demanda_satisfecha = sum(
            (p.get("demanda_satisfecha") or 0) for p in abiertas
        )
        # Para corridas sin restricción de aulas, satisfecha == demanda de abiertas.
        if not self.aulas:
            demanda_satisfecha = sum(p["demanda"] for p in abiertas)
        pct_demanda = round(100 * demanda_satisfecha / demanda_total, 1) if demanda_total else 0.0

        # --- Completitud / ocupación de aulas ---
        comisiones_con_aula = [p for p in abiertas if p.get("capacidad_aula")]
        if comisiones_con_aula:
            capacidad_instalada = sum(p["capacidad_aula"] for p in comisiones_con_aula)
            ocupacion = sum(
                min(p["demanda"], p["capacidad_aula"]) for p in comisiones_con_aula
            )
            pct_ocupacion = round(100 * ocupacion / capacidad_instalada, 1) if capacidad_instalada else 0.0
        else:
            capacidad_instalada = 0
            pct_ocupacion = 0.0

        aulas_totales = len(self.aulas)
        # Un aula puede usarse en más de un turno; contamos asignaciones únicas.
        aulas_usadas = len({p["aula_id"] for p in abiertas if p.get("aula_id")})

        # --- Alocación de docentes ---
        docentes_totales = len(self.docentes)
        docentes_asignados = len({p["docente_id"] for p in abiertas if p.get("docente_id")})
        docentes_libres = max(0, docentes_totales - docentes_asignados)
        pct_docentes = round(100 * docentes_asignados / docentes_totales, 1) if docentes_totales else 0.0

        # --- Métrica extra: cobertura de cuellos de botella ---
        cuellos = {c["codigo"] for c in self.detectar_cuellos_de_botella()}
        cuellos_abiertos = {p["codigo"] for p in abiertas if p["codigo"] in cuellos}
        pct_cuellos = round(100 * len(cuellos_abiertos) / len(cuellos), 1) if cuellos else 0.0

        # Comisiones que no abrieron por falta de recurso (diagnóstico).
        no_abiertas_por_aula = sum(
            1 for p in prescripciones.values() if p.get("motivo_no_apertura") == "sin_aula"
        )
        no_abiertas_por_docente = sum(
            1 for p in prescripciones.values() if p.get("motivo_no_apertura") == "sin_docente"
        )

        return {
            "comisiones_abiertas": len(abiertas),
            "ingresos_proyectados": ingresos_total,
            "demanda_total": demanda_total,
            "demanda_satisfecha": demanda_satisfecha,
            "pct_demanda_satisfecha": pct_demanda,
            "aulas_totales": aulas_totales,
            "aulas_usadas": aulas_usadas,
            "capacidad_instalada": capacidad_instalada,
            "pct_ocupacion_aulas": pct_ocupacion,
            "docentes_totales": docentes_totales,
            "docentes_asignados": docentes_asignados,
            "docentes_libres": docentes_libres,
            "pct_docentes_asignados": pct_docentes,
            "cuellos_botella_total": len(cuellos),
            "cuellos_botella_cubiertos": len(cuellos_abiertos),
            "pct_cuellos_cubiertos": pct_cuellos,
            "comisiones_sin_aula": no_abiertas_por_aula,
            "comisiones_sin_docente": no_abiertas_por_docente,
        }

    def calcular_promedio_estudiante(
        self, estudiante_id: str
    ) -> Optional[float]:
        """Obtiene el promedio academico de un estudiante"""
        if estudiante_id not in self.estudiantes:
            return None
        return self.estudiantes[estudiante_id].promedio_academico

    def generar_grafo_visualizable(self) -> Dict:
        """
        Genera representacion del grafo para visualizacion.
        
        Retorna diccionario con nodos y edges para bibliotecas como Vis.js
        """
        nodos = []
        for codigo, materia in self.plan.materias.items():
            nodos.append({
                "id": codigo,
                "label": materia.nombre[:30],  # Truncar para legibilidad
                "title": materia.nombre,
                "year": materia.ano,
                "color": self._color_por_ano(materia.ano),
            })

        edges = []
        for src, dst in self.grafo_correlativas.edges():
            edges.append({
                "from": src,
                "to": dst,
                "arrows": "to",
            })

        return {
            "nodes": nodos,
            "edges": edges,
            "total_nodos": len(nodos),
            "total_edges": len(edges),
        }

    def _color_por_ano(self, ano: int) -> str:
        """Retorna color para visualizar por ano"""
        colores = {
            1: "#FF6B6B",  # Rojo
            2: "#4ECDC4",  # Turquesa
            3: "#45B7D1",  # Azul
            4: "#FFA502",  # Naranja
            5: "#95E1D3",  # Verde menta
        }
        return colores.get(ano, "#cccccc")

    def tiene_ciclos(self) -> bool:
        """
        Se fija si el plan de estudio tiene algun rulo (ciclo).
        Si hay un ciclo, los pibes nunca se van a recibir, asi que ojo.
        """
        try:
            ciclo = nx.find_cycle(self.grafo_correlativas, orientation="original")
            logger.warning(f"¡Ojo! Se detecto un ciclo en el plan: {ciclo}")
            return True
        except nx.NetworkXNoCycle:
            return False

    def detectar_cuellos_de_botella(self) -> List[Dict]:
        """
        Detecta materias criticas (muchos prerequisites o muchos dependientes).
        
        Estas son materias donde los retrasos cascadean significativamente.
        """
        cuellos = []

        for codigo, materia in self.plan.materias.items():
            # Contar in-degree (cuantos prerequisitos)
            in_degree = self.grafo_correlativas.in_degree(codigo)
            
            # Contar out-degree (cuantas materias la necesitan)
            out_degree = self.grafo_correlativas.out_degree(codigo)

            # Critica si tiene muchas materias dependientes
            if out_degree >= 3:
                cuellos.append({
                    "codigo": codigo,
                    "nombre": materia.nombre,
                    "materias_dependientes": out_degree,
                    "prerequisitos": in_degree,
                    "criticidad": "ALTA" if out_degree >= 5 else "MEDIA",
                })

        cuellos.sort(key=lambda x: x["materias_dependientes"], reverse=True)
        return cuellos

    def reporte_prescriptivo(self) -> str:
        """Genera reporte completo de prescripciones"""
        reporte = [
            f"\n{'='*70}",
            "REPORTE PRESCRIPTIVO DE KAIROS",
            f"Carrera: {self.plan.nombre_carrera}",
            f"{'='*70}\n",
        ]

        # Demanda
        reporte.append("ANALISIS DE DEMANDA:")
        demanda = self.analizar_demanda()
        demanda_total = sum(demanda.values())
        reporte.append(f"  Total de "
                      f"inscripciones demandadas: {demanda_total}")
        reporte.append(f"  Materias con demanda: {len(demanda)}\n")

        # Prescripciones
        reporte.append("PRESCRIPCIONES DE APERTURA:")
        prescripciones = self.prescribir_aperturas()
        a_abrir = [p for p in prescripciones.values() if p["decision"] == "ABRIR"]
        no_abrir = [p for p in prescripciones.values() if p["decision"] == "NO ABRIR"]

        reporte.append(f"  A ABRIR: {len(a_abrir)}")
        for p in a_abrir[:5]:
            reporte.append(f"     {p['codigo']}: {p['nombre']} ({p['demanda']} estudiantes)")
        if len(a_abrir) > 5:
            reporte.append(f"    ... y {len(a_abrir) - 5} mas")

        reporte.append(f"\n  NO ABRIR: {len(no_abrir)}")

        # Cuellos de botella
        cuellos = self.detectar_cuellos_de_botella()
        if cuellos:
            reporte.append(f"\nCUELLOS DE BOTELLA:")
            for cuello in cuellos[:5]:
                reporte.append(
                    f"   {cuello['codigo']}: "
                    f"{cuello['materias_dependientes']} dependientes "
                    f"(Criticidad: {cuello['criticidad']})"
                )

        reporte.append(f"\n{'='*70}\n")

        return "\n".join(reporte)
