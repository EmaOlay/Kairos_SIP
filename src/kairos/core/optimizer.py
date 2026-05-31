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
        Aristas: X  Y significa que X es prerequisito de Y (debe aprobarse antes)
        """
        logger.info("Inicializando grafo de correlatividades...")

        for codigo, materia in self.plan.materias.items():
            self.grafo_correlativas.add_node(codigo, materia=materia)

        for codigo, materia in self.plan.materias.items():
            for prerequisito in materia.correlativas_anteriores:
                if prerequisito in self.plan.materias:
                    self.grafo_correlativas.add_edge(prerequisito, codigo)

        logger.info(
            f" Grafo construido: {len(self.grafo_correlativas.nodes)} nodos, "
            f"{len(self.grafo_correlativas.edges)} aristas"
        )

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
        
        Un estudiante "necesita" una materia si:
        - Aun no la aprobo
        - Cumple todos los prerequisitos
        """
        self.demanda_por_materia.clear()

        for est in self.estudiantes.values():
            materias_disponibles = self._calcular_materias_disponibles(est)

            for codigo in materias_disponibles:
                self.demanda_por_materia[codigo].add(est.estudiante_id)

        # Convertir a conteo
        demanda = {k: len(v) for k, v in self.demanda_por_materia.items()}

        # Log de top 10
        top_10 = sorted(demanda.items(), key=lambda x: x[1], reverse=True)[:10]
        logger.info("Top 10 materias por demanda:")
        for codigo, cantidad in top_10:
            materia = self.plan.materias[codigo]
            logger.info(f"  {codigo}: {materia.nombre} ({cantidad} estudiantes)")

        return demanda

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

    def prescribir_aperturas(self) -> Dict[str, Dict]:
        """
        Prescribe que comisiones abrir para el proximo periodo.
        
        Optimiza balanceando:
        - Maximizar materias demandadas (graduacion)
        - Minimizar costos operativos (eficiencia)
        - Respetar restricciones de ocupacion minima
        
        Retorna: {codigo_materia: {decision, razon, estudiantes_demandantes}}
        """
        logger.info("Analizando demanda y prescribiendo aperturas...")

        demanda = self.analizar_demanda()

        prescripciones = {}

        for codigo, cantidad in demanda.items():
            materia = self.plan.materias[codigo]

            # Decidir si abrir basado en demanda vs. configuracion
            tasa_necesaria = self.config.min_tasa_ocupacion
            cupos_minimos = int(self.config.max_cupos_por_comision * tasa_necesaria)

            decision = "ABRIR" if cantidad >= cupos_minimos else "NO ABRIR"

            razon = (
                f"Demanda de {cantidad} estudiantes "
                f"(minimo: {cupos_minimos})"
            )

            prescripciones[codigo] = {
                "codigo": codigo,
                "nombre": materia.nombre,
                "decision": decision,
                "razon": razon,
                "demanda": cantidad,
                "estudiantes_demandantes": list(self.demanda_por_materia[codigo]),
            }

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
