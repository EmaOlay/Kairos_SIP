"""
Tests de las restricciones operativas del motor (aulas + docentes + historico).

Cubren que la feature es ADITIVA (sin datos, el motor se comporta como antes)
y que las restricciones duras se aplican cuando hay datos cargados.
"""

import pytest

from kairos.core.optimizer import KairosOptimizer
from kairos.schemas.data_models import (
    Aula,
    ConfiguracionKairos,
    Docente,
    EstudianteTrayectoria,
    HistoricoDictado,
)


def _poblar_demanda(optimizer, codigo="3.4.069", turno="noche", n=30):
    """Agrega n estudiantes que demandan `codigo` en `turno`."""
    for i in range(n):
        optimizer.agregar_estudiante(
            EstudianteTrayectoria(
                estudiante_id=f"EST{i:03d}",
                codigo_carrera="ING_INF",
                plan_estudio_id="1621",
                ano_ingreso=2023,
                turno_preferido=turno,
            )
        )


class TestRetrocompatibilidad:
    """Sin aulas ni docentes cargados, el motor decide solo por score."""

    def test_sin_recursos_abre_por_score(self, plan_estudio_minimo):
        config = ConfiguracionKairos(min_tasa_ocupacion=0.0)
        optimizer = KairosOptimizer(plan_estudio_minimo, config)
        _poblar_demanda(optimizer, n=30)

        prescripciones = optimizer.prescribir_aperturas()
        assert prescripciones["3.4.069_noche"]["decision"] == "ABRIR"
        # Sin restriccion de aula, toda la demanda queda satisfecha.
        p = prescripciones["3.4.069_noche"]
        assert p["demanda_satisfecha"] == 30
        assert p["motivo_no_apertura"] is None


class TestRestriccionDocentes:
    def test_no_abre_sin_docente_disponible(self, plan_estudio_minimo):
        """Si hay docentes cargados pero ninguno puede dictar, no se abre."""
        config = ConfiguracionKairos(min_tasa_ocupacion=0.0)
        optimizer = KairosOptimizer(plan_estudio_minimo, config)
        _poblar_demanda(optimizer, n=30)
        # Docente que dicta OTRA materia: no sirve para 3.4.069.
        optimizer.agregar_docentes(
            [
                Docente(
                    docente_id="DOCX",
                    nombre="Ing. X",
                    materias_que_dicta=["9.9.999"],
                    disponibilidad_turnos=["noche"],
                )
            ]
        )
        prescripciones = optimizer.prescribir_aperturas()
        p = prescripciones["3.4.069_noche"]
        assert p["decision"] == "NO ABRIR"
        assert p["motivo_no_apertura"] == "sin_docente"

    def test_abre_con_docente_habilitado(
        self, plan_estudio_minimo, docente_fundamentos
    ):
        config = ConfiguracionKairos(min_tasa_ocupacion=0.0)
        optimizer = KairosOptimizer(plan_estudio_minimo, config)
        _poblar_demanda(optimizer, n=30)
        optimizer.agregar_docentes([docente_fundamentos])

        p = optimizer.prescribir_aperturas()["3.4.069_noche"]
        assert p["decision"] == "ABRIR"
        assert p["docente"] == "Ing. Ana Lopez"
        assert p["docente_id"] == "DOC001"

    def test_tope_de_carga_docente(self, plan_estudio_minimo, docente_fundamentos):
        """Un docente con max_comisiones=2 no puede tomar una 3ra comision."""
        config = ConfiguracionKairos(min_tasa_ocupacion=0.0)
        optimizer = KairosOptimizer(plan_estudio_minimo, config)
        # Demanda en los 3 turnos de la misma materia.
        for turno in ("manana", "tarde", "noche"):
            _poblar_demanda(optimizer, turno=turno, n=20)
        # Docente disponible en los 3 turnos, pero tope 2.
        optimizer.agregar_docentes(
            [
                Docente(
                    docente_id="DOC001",
                    nombre="Ing. Ana Lopez",
                    materias_que_dicta=["3.4.069"],
                    disponibilidad_turnos=["manana", "tarde", "noche"],
                    max_comisiones=2,
                )
            ]
        )
        prescripciones = optimizer.prescribir_aperturas()
        abiertas = [
            k for k, p in prescripciones.items()
            if k.startswith("3.4.069_") and p["decision"] == "ABRIR"
        ]
        # Solo 2 comisiones pueden abrir (tope de carga del unico docente).
        assert len(abiertas) == 2


class TestRestriccionAulas:
    def test_capacidad_limita_cupos(
        self, plan_estudio_minimo, docente_fundamentos
    ):
        """La capacidad del aula limita los cupos; el resto queda sin cupo."""
        config = ConfiguracionKairos(min_tasa_ocupacion=0.0)
        optimizer = KairosOptimizer(plan_estudio_minimo, config)
        _poblar_demanda(optimizer, n=50)  # 50 alumnos
        optimizer.agregar_docentes([docente_fundamentos])
        optimizer.agregar_aulas(
            [Aula(aula_id="A1", nombre="Chica", capacidad=30, turnos_disponibles=["noche"])]
        )
        p = optimizer.prescribir_aperturas()["3.4.069_noche"]
        assert p["decision"] == "ABRIR"
        assert p["capacidad_aula"] == 30
        assert p["demanda_satisfecha"] == 30
        assert p["demanda_no_satisfecha"] == 20  # 50 - 30

    def test_sin_aulas_libres_no_abre(self, plan_estudio_minimo):
        """Mas comisiones que aulas en el turno => las sobrantes no abren."""
        config = ConfiguracionKairos(min_tasa_ocupacion=0.0)
        optimizer = KairosOptimizer(plan_estudio_minimo, config)
        for turno in ("manana", "tarde", "noche"):
            _poblar_demanda(optimizer, turno=turno, n=20)
        # Solo 1 aula que sirve de noche => solo 1 de las 3 franjas puede abrir.
        optimizer.agregar_aulas(
            [Aula(aula_id="A1", nombre="Unica", capacidad=40, turnos_disponibles=["noche"])]
        )
        prescripciones = optimizer.prescribir_aperturas()
        abiertas = [
            p for k, p in prescripciones.items()
            if k.startswith("3.4.069_") and p["decision"] == "ABRIR"
        ]
        assert len(abiertas) == 1
        assert abiertas[0]["turno"] == "noche"

    def test_flag_desactiva_restriccion_aulas(self, plan_estudio_minimo):
        """Con respetar_capacidad_aulas=False, las aulas no restringen."""
        config = ConfiguracionKairos(min_tasa_ocupacion=0.0, respetar_capacidad_aulas=False)
        optimizer = KairosOptimizer(plan_estudio_minimo, config)
        _poblar_demanda(optimizer, n=50)
        optimizer.agregar_aulas(
            [Aula(aula_id="A1", nombre="Chica", capacidad=10, turnos_disponibles=["noche"])]
        )
        p = optimizer.prescribir_aperturas()["3.4.069_noche"]
        # Sin restriccion: abre y satisface toda la demanda pese al aula chica.
        assert p["decision"] == "ABRIR"
        assert p["demanda_satisfecha"] == 50


class TestEstimacionHistorico:
    def test_estima_disponibilidad_desde_historico(
        self, plan_estudio_minimo, docente_sin_horario, historico_fundamentos
    ):
        """
        Un docente sin horario fehaciente igual puede ser asignado si el
        historico muestra que dicto esa materia en ese turno.
        """
        config = ConfiguracionKairos(min_tasa_ocupacion=0.0)
        optimizer = KairosOptimizer(plan_estudio_minimo, config)
        _poblar_demanda(optimizer, n=30)
        optimizer.agregar_docentes([docente_sin_horario])
        optimizer.agregar_historico([historico_fundamentos])

        p = optimizer.prescribir_aperturas()["3.4.069_noche"]
        assert p["decision"] == "ABRIR"
        assert p["docente_id"] == "DOC002"

    def test_sin_historico_no_estima(self, plan_estudio_minimo, docente_sin_horario):
        """Sin historico, el docente sin disponibilidad no se puede asignar."""
        config = ConfiguracionKairos(min_tasa_ocupacion=0.0)
        optimizer = KairosOptimizer(plan_estudio_minimo, config)
        _poblar_demanda(optimizer, n=30)
        optimizer.agregar_docentes([docente_sin_horario])

        p = optimizer.prescribir_aperturas()["3.4.069_noche"]
        assert p["decision"] == "NO ABRIR"
        assert p["motivo_no_apertura"] == "sin_docente"


class TestMetricasOperativas:
    def test_metricas_basicas(
        self, plan_estudio_minimo, docente_fundamentos, aula_basica
    ):
        config = ConfiguracionKairos(min_tasa_ocupacion=0.0)
        optimizer = KairosOptimizer(plan_estudio_minimo, config)
        _poblar_demanda(optimizer, n=30)
        optimizer.agregar_docentes([docente_fundamentos])
        optimizer.agregar_aulas([aula_basica])

        prescripciones = optimizer.prescribir_aperturas()
        m = optimizer.metricas_operativas(prescripciones)

        assert m["comisiones_abiertas"] >= 1
        assert m["docentes_totales"] == 1
        assert m["docentes_asignados"] == 1
        assert m["docentes_libres"] == 0
        assert m["pct_docentes_asignados"] == 100.0
        assert m["aulas_totales"] == 1
        # 30 alumnos en aula de 40 => ocupacion 75%.
        assert m["pct_ocupacion_aulas"] == 75.0
        assert m["ingresos_proyectados"] == 30 * 6000  # turno noche

    def test_demanda_satisfecha_con_aula_chica(
        self, plan_estudio_minimo, docente_fundamentos
    ):
        config = ConfiguracionKairos(min_tasa_ocupacion=0.0)
        optimizer = KairosOptimizer(plan_estudio_minimo, config)
        _poblar_demanda(optimizer, n=50)
        optimizer.agregar_docentes([docente_fundamentos])
        optimizer.agregar_aulas(
            [Aula(aula_id="A1", nombre="Chica", capacidad=30, turnos_disponibles=["noche"])]
        )
        m = optimizer.metricas_operativas()
        # Solo 30 de 50 quedan satisfechos; ingreso por los 30 con cupo.
        assert m["demanda_satisfecha"] == 30
        assert m["ingresos_proyectados"] == 30 * 6000
