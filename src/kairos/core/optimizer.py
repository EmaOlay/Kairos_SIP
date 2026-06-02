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
    EstudianteTrayectoria,
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

    def prescribir_aperturas(self) -> Dict[str, Dict]:
        """
        Prescribe que comisiones abrir por materia+turno.

        Splitea la demanda por turno preferido del alumno, calcula el score
        de cada combinación materia+turno usando cascada + demanda/costo,
        y rankea para decidir cuáles abrir.
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

        for codigo, turno, materia, score, cantidad, cascada, ingreso, est_list in ranking:
            supera_minimo = score >= score_minimo

            if supera_minimo and (tope is None or abiertas < tope):
                decision = "ABRIR"
                razon = (
                    f"Score {score} ≥ mínimo {score_minimo:.1f}. "
                    f"Desbloquea {cascada} materias y junta {cantidad} alumnos "
                    f"(${int(cantidad * ingreso):,} de ingreso)."
                )
                abiertas += 1
            elif not supera_minimo:
                razon = (
                    f"Score {score} < mínimo {score_minimo:.1f}. "
                    f"Demanda baja ({cantidad} alumnos) o poco impacto en cascada ({cascada})."
                )
                decision = "NO ABRIR"
            else:
                razon = (
                    f"Tope presupuestario alcanzado ({tope} comisiones). "
                    f"Score {score} no entró en el ranking."
                )
                decision = "NO ABRIR"

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
            }

        prescripciones = dict(
            sorted(prescripciones.items(), key=lambda x: x[1]["score"], reverse=True)
        )

        return prescripciones

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
