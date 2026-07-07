"""
Tests unitarios para KairosOptimizer.radiografia_estudiante

Clasifica todo el plan de un alumno en cuatro grupos (aprobadas / pendientes
de final / disponibles a cursar / bloqueadas) aplicando las correlatividades
en dos niveles: cursar exige la anterior al menos REGULAR, rendir el final
exige la anterior APROBADA.
"""

import pytest

from kairos.core.optimizer import KairosOptimizer
from kairos.schemas.data_models import (
    EstadoMateria,
    EstudianteTrayectoria,
    Materia,
    PlanEstudio,
    RegistroTrayectoria,
)


def _materia(codigo, ano, cuatri, prereqs=None):
    return Materia(
        codigo=codigo,
        nombre=f"Materia {codigo}",
        ano=ano,
        cuatrimestre=cuatri,
        correlativas_anteriores=prereqs or [],
    )


@pytest.fixture
def plan_cadena():
    """Plan en cadena A -> B -> C -> D (cada una prereq de la siguiente)."""
    materias = {
        "A": _materia("A", 1, 1),
        "B": _materia("B", 1, 2, ["A"]),
        "C": _materia("C", 2, 1, ["B"]),
        "D": _materia("D", 2, 2, ["C"]),
    }
    return PlanEstudio(
        codigo_plan="TEST",
        nombre_carrera="Carrera Test",
        ano_vigencia=2021,
        duracion_anos=5,
        materias=materias,
    )


def _registro(codigo, estado):
    return RegistroTrayectoria(
        codigo_materia=codigo,
        nombre_materia=f"Materia {codigo}",
        estado=estado,
        ano_academico=2024,
        cuatrimestre=1,
    )


def _estudiante(registros):
    return EstudianteTrayectoria(
        estudiante_id="EST001",
        codigo_carrera="ING_INF",
        plan_estudio_id="TEST",
        ano_ingreso=2023,
        registros_trayectoria=registros,
    )


class TestRadiografiaBuckets:
    """La radiografia parte el plan en los cuatro grupos correctos."""

    def test_cuatro_buckets_en_una_cadena(self, plan_cadena):
        """A aprobada, B regular -> C disponible (final condicionado), D bloqueada."""
        optimizer = KairosOptimizer(plan_cadena)
        estudiante = _estudiante([
            _registro("A", EstadoMateria.APROBADA),
            _registro("B", EstadoMateria.REGULAR),
        ])

        radio = optimizer.radiografia_estudiante(estudiante)

        assert [m["codigo"] for m in radio["aprobadas"]] == ["A"]
        assert [m["codigo"] for m in radio["pendientes_de_final"]] == ["B"]
        assert [m["codigo"] for m in radio["disponibles_a_cursar"]] == ["C"]
        assert [m["codigo"] for m in radio["bloqueadas"]] == ["D"]

    def test_cada_materia_cae_en_exactamente_un_bucket(self, plan_cadena):
        """Ningun codigo se duplica ni se pierde entre los cuatro grupos."""
        optimizer = KairosOptimizer(plan_cadena)
        estudiante = _estudiante([
            _registro("A", EstadoMateria.APROBADA),
            _registro("B", EstadoMateria.REGULAR),
        ])

        radio = optimizer.radiografia_estudiante(estudiante)
        codigos = [
            m["codigo"]
            for grupo in ("aprobadas", "pendientes_de_final",
                          "disponibles_a_cursar", "bloqueadas")
            for m in radio[grupo]
        ]
        assert sorted(codigos) == ["A", "B", "C", "D"]
        assert len(codigos) == len(set(codigos))

    def test_alumno_nuevo_solo_ve_materias_sin_prereqs(self, plan_cadena):
        """Sin registros: solo la raiz (A) es cursable, el resto bloqueado."""
        optimizer = KairosOptimizer(plan_cadena)
        radio = optimizer.radiografia_estudiante(_estudiante([]))

        assert radio["aprobadas"] == []
        assert radio["pendientes_de_final"] == []
        assert [m["codigo"] for m in radio["disponibles_a_cursar"]] == ["A"]
        assert sorted(m["codigo"] for m in radio["bloqueadas"]) == ["B", "C", "D"]

    def test_disponible_sin_condicion_cuando_prereq_aprobada(self, plan_cadena):
        """Si la correlativa esta aprobada, la materia queda 100% habilitada."""
        optimizer = KairosOptimizer(plan_cadena)
        estudiante = _estudiante([_registro("A", EstadoMateria.APROBADA)])

        radio = optimizer.radiografia_estudiante(estudiante)
        disp = {m["codigo"]: m for m in radio["disponibles_a_cursar"]}
        assert "B" in disp
        assert disp["B"]["final_condicionado"] is False
        assert disp["B"]["correlativas_a_aprobar_para_final"] == []


class TestFinalCondicionado:
    """Regla de dos niveles: cursar con regular, rendir final con aprobada."""

    def test_final_condicionado_si_prereq_solo_regular(self, plan_cadena):
        """B regular habilita cursar C pero deja su final condicionado a aprobar B."""
        optimizer = KairosOptimizer(plan_cadena)
        estudiante = _estudiante([
            _registro("A", EstadoMateria.APROBADA),
            _registro("B", EstadoMateria.REGULAR),
        ])

        radio = optimizer.radiografia_estudiante(estudiante)
        c = next(m for m in radio["disponibles_a_cursar"] if m["codigo"] == "C")
        assert c["final_condicionado"] is True
        assert c["correlativas_a_aprobar_para_final"] == ["B"]

    def test_pendiente_puede_rendir_final_si_prereq_aprobada(self, plan_cadena):
        """B regular con A aprobada: ya puede rendir el final de B."""
        optimizer = KairosOptimizer(plan_cadena)
        estudiante = _estudiante([
            _registro("A", EstadoMateria.APROBADA),
            _registro("B", EstadoMateria.REGULAR),
        ])

        radio = optimizer.radiografia_estudiante(estudiante)
        b = next(m for m in radio["pendientes_de_final"] if m["codigo"] == "B")
        assert b["puede_rendir_final"] is True
        assert b["correlativas_faltantes_final"] == []

    def test_pendiente_no_puede_rendir_si_prereq_no_aprobada(self, plan_cadena):
        """B regular pero A solo regular: no puede rendir el final de B todavia."""
        optimizer = KairosOptimizer(plan_cadena)
        estudiante = _estudiante([
            _registro("A", EstadoMateria.REGULAR),
            _registro("B", EstadoMateria.REGULAR),
        ])

        radio = optimizer.radiografia_estudiante(estudiante)
        b = next(m for m in radio["pendientes_de_final"] if m["codigo"] == "B")
        assert b["puede_rendir_final"] is False
        assert b["correlativas_faltantes_final"] == ["A"]


class TestBloqueadas:
    """Las bloqueadas informan que correlativas faltan para poder cursar."""

    def test_bloqueada_lista_correlativas_faltantes(self, plan_cadena):
        """D esta bloqueada porque C no llega ni a regular."""
        optimizer = KairosOptimizer(plan_cadena)
        estudiante = _estudiante([
            _registro("A", EstadoMateria.APROBADA),
            _registro("B", EstadoMateria.REGULAR),
        ])

        radio = optimizer.radiografia_estudiante(estudiante)
        d = next(m for m in radio["bloqueadas"] if m["codigo"] == "D")
        assert d["correlativas_faltantes"] == ["C"]


class TestOrdenYResumen:
    """Orden por impacto de cascada y contadores del resumen."""

    def test_disponibles_ordenadas_por_impacto_cascada(self):
        """Entre dos disponibles, primero la que desbloquea mas materias."""
        # Plan: RAIZ desbloquea una cadena larga; SUELTA no desbloquea nada.
        materias = {
            "RAIZ": _materia("RAIZ", 1, 1),
            "H1": _materia("H1", 1, 2, ["RAIZ"]),
            "H2": _materia("H2", 2, 1, ["H1"]),
            "SUELTA": _materia("SUELTA", 1, 1),
        }
        plan = PlanEstudio(
            codigo_plan="TEST2",
            nombre_carrera="Carrera Test 2",
            ano_vigencia=2021,
            duracion_anos=5,
            materias=materias,
        )
        optimizer = KairosOptimizer(plan)
        radio = optimizer.radiografia_estudiante(_estudiante([]))

        disponibles = [m["codigo"] for m in radio["disponibles_a_cursar"]]
        assert disponibles == ["RAIZ", "SUELTA"]
        raiz = radio["disponibles_a_cursar"][0]
        assert raiz["impacto_cascada"] == 2  # H1 y H2

    def test_resumen_cuenta_y_porcentaje(self, plan_cadena):
        """El resumen refleja los tamanos de cada grupo y el avance."""
        optimizer = KairosOptimizer(plan_cadena)
        estudiante = _estudiante([
            _registro("A", EstadoMateria.APROBADA),
            _registro("B", EstadoMateria.REGULAR),
        ])

        radio = optimizer.radiografia_estudiante(estudiante)
        resumen = radio["resumen"]
        assert resumen["total_materias"] == 4
        assert resumen["aprobadas"] == 1
        assert resumen["pendientes_de_final"] == 1
        assert resumen["disponibles_a_cursar"] == 1
        assert resumen["bloqueadas"] == 1
        assert resumen["porcentaje_avance"] == 25.0

    def test_metadatos_estudiante_y_plan(self, plan_cadena):
        """La radiografia identifica al alumno y su plan."""
        optimizer = KairosOptimizer(plan_cadena)
        radio = optimizer.radiografia_estudiante(_estudiante([]))
        assert radio["estudiante_id"] == "EST001"
        assert radio["plan"] == "TEST"
        assert radio["carrera"] == "Carrera Test"
