"""
Tests unitarios para kairos.schemas.data_models
"""

import pytest
from datetime import datetime
from pydantic import ValidationError

from kairos.schemas.data_models import (
    EstadoMateria,
    RegistroTrayectoria,
    EstudianteTrayectoria,
    Materia,
    PlanEstudio,
    RecursoDisponible,
)


class TestEstadoMateria:
    """Tests para el enum EstadoMateria"""

    def test_estados_validos(self):
        """Verifica que todos los estados existan"""
        assert EstadoMateria.APROBADA.value == "aprobada"
        assert EstadoMateria.REGULAR.value == "regular"
        assert EstadoMateria.INSCRIPTA.value == "inscripta"
        assert EstadoMateria.PENDIENTE.value == "pendiente"

    def test_estado_from_string(self):
        """Verifica que se puedan crear estados desde strings"""
        estado = EstadoMateria("aprobada")
        assert estado == EstadoMateria.APROBADA


class TestRegistroTrayectoria:
    """Tests para RegistroTrayectoria"""

    def test_registro_valido_aprobada(self, registro_trayectoria_aprobada):
        """Verifica que un registro valido se crea correctamente"""
        assert registro_trayectoria_aprobada.codigo_materia == "3.4.069"
        assert registro_trayectoria_aprobada.estado == EstadoMateria.APROBADA
        assert registro_trayectoria_aprobada.calificacion == 8.5

    def test_calificacion_fuera_de_rango(self):
        """Verifica que calificacion > 10 falla"""
        with pytest.raises(ValidationError):
            RegistroTrayectoria(
                codigo_materia="3.4.069",
                nombre_materia="Test",
                estado=EstadoMateria.APROBADA,
                ano_academico=2023,
                cuatrimestre=1,
                calificacion=11.0,
            )

    def test_calificacion_negativa(self):
        """Verifica que calificacion < 0 falla"""
        with pytest.raises(ValidationError):
            RegistroTrayectoria(
                codigo_materia="3.4.069",
                nombre_materia="Test",
                estado=EstadoMateria.APROBADA,
                ano_academico=2023,
                cuatrimestre=1,
                calificacion=-1.0,
            )

    def test_calificacion_none_valida(self):
        """Verifica que calificacion None es valida (para cursos sin evaluar)"""
        registro = RegistroTrayectoria(
            codigo_materia="3.4.069",
            nombre_materia="Test",
            estado=EstadoMateria.INSCRIPTA,
            ano_academico=2024,
            cuatrimestre=1,
            calificacion=None,
        )
        assert registro.calificacion is None

    def test_campos_requeridos(self):
        """Verifica que campos requeridos son obligatorios"""
        with pytest.raises(ValidationError):
            RegistroTrayectoria(
                # Faltan campos requeridos
                ano_academico=2023,
            )


class TestEstudianteTrayectoria:
    """Tests para EstudianteTrayectoria"""

    def test_estudiante_basico(self, estudiante_basico):
        """Verifica que un estudiante se crea correctamente"""
        assert estudiante_basico.estudiante_id == "EST001"
        assert len(estudiante_basico.registros_trayectoria) == 2

    def test_materias_aprobadas(self, estudiante_basico):
        """Verifica que materias_aprobadas retorna solo aprobadas"""
        aprobadas = estudiante_basico.materias_aprobadas
        assert "3.4.069" in aprobadas
        assert "3.4.070" not in aprobadas
        assert len(aprobadas) == 1

    def test_materias_cursando(self, estudiante_basico):
        """Verifica que materias_cursando retorna inscritas y regulares"""
        cursando = estudiante_basico.materias_cursando
        assert "3.4.070" in cursando
        assert "3.4.069" not in cursando
        assert len(cursando) == 1

    def test_promedio_academico(self, estudiante_basico):
        """Verifica que promedio se calcula correctamente"""
        promedio = estudiante_basico.promedio_academico
        assert promedio == 8.5  # Solo una materia aprobada con calif 8.5

    def test_promedio_academico_sin_aprobadas(self):
        """Verifica que promedio es None si no hay aprobadas"""
        estudiante = EstudianteTrayectoria(
            estudiante_id="EST002",
            codigo_carrera="ING_INF",
            plan_estudio_id="1621",
            ano_ingreso=2024,
            registros_trayectoria=[],
        )
        assert estudiante.promedio_academico is None

    def test_registros_trayectoria_vacia(self):
        """Verifica que se puede crear estudiante sin registros"""
        estudiante = EstudianteTrayectoria(
            estudiante_id="EST003",
            codigo_carrera="ING_INF",
            plan_estudio_id="1621",
            ano_ingreso=2023,
        )
        assert len(estudiante.registros_trayectoria) == 0
        assert len(estudiante.materias_aprobadas) == 0


class TestMateria:
    """Tests para Materia"""

    def test_materia_basica(self, materia_basica):
        """Verifica que una materia se crea correctamente"""
        assert materia_basica.codigo == "3.4.069"
        assert materia_basica.ano == 1
        assert materia_basica.cuatrimestre == 1

    def test_horas_totales(self, materia_basica):
        """Verifica que horas_totales suma teoricas + practicas"""
        assert materia_basica.horas_totales == 60

    def test_correlativas(self, materia_con_correlativas):
        """Verifica que correlativas se guardan correctamente"""
        assert "3.4.069" in materia_con_correlativas.correlativas_anteriores
        assert len(materia_con_correlativas.correlativas_anteriores) == 1

    def test_horas_totales_parciales(self):
        """Verifica que horas_totales funciona con valores 0 o None"""
        materia = Materia(
            codigo="3.4.071",
            nombre="Test",
            ano=1,
            cuatrimestre=1,
            horas_teoricas=40,
            horas_practicas=None,
        )
        assert materia.horas_totales == 40


class TestPlanEstudio:
    """Tests para PlanEstudio"""

    def test_plan_basico(self, plan_estudio_minimo):
        """Verifica que un plan se crea correctamente"""
        assert plan_estudio_minimo.codigo_plan == "1621"
        assert len(plan_estudio_minimo.materias) == 2

    def test_materias_por_ano(self, plan_estudio_minimo):
        """Verifica que materias_por_ano agrupa correctamente"""
        por_ano = plan_estudio_minimo.materias_por_ano
        assert 1 in por_ano
        assert len(por_ano[1]) == 2

    def test_materias_por_cuatrimestre(self, plan_estudio_minimo):
        """Verifica que materias_por_cuatrimestre agrupa correctamente"""
        por_cuatri = plan_estudio_minimo.materias_por_cuatrimestre
        assert (1, 1) in por_cuatri  # (ano, cuatrimestre)
        assert (1, 2) in por_cuatri
        assert len(por_cuatri[(1, 1)]) == 1
        assert len(por_cuatri[(1, 2)]) == 1

    def test_obtener_correlativas_existe(self, plan_estudio_minimo):
        """Verifica obtener_correlativas para materia existente"""
        anteriores, posteriores = plan_estudio_minimo.obtener_correlativas("3.4.070")
        assert "3.4.069" in anteriores

    def test_obtener_correlativas_no_existe(self, plan_estudio_minimo):
        """Verifica obtener_correlativas para materia inexistente"""
        anteriores, posteriores = plan_estudio_minimo.obtener_correlativas("9.9.999")
        assert anteriores == []
        assert posteriores == []


class TestRecursoDisponible:
    """Tests para RecursoDisponible"""

    def test_recurso_basico(self, recurso_disponible_basico):
        """Verifica que un recurso se crea correctamente"""
        assert recurso_disponible_basico.recurso_id == "COM001"
        assert recurso_disponible_basico.cupos_totales == 50

    def test_cupos_disponibles(self, recurso_disponible_basico):
        """Verifica que cupos_disponibles se calcula correctamente"""
        # 50 totales - 30 ocupados = 20 disponibles
        assert recurso_disponible_basico.cupos_disponibles == 20

    def test_cupos_disponibles_lleno(self, recurso_disponible_lleno):
        """Verifica que cupos_disponibles es 0 cuando esta lleno"""
        assert recurso_disponible_lleno.cupos_disponibles == 0

    def test_tasa_ocupacion(self, recurso_disponible_basico):
        """Verifica que tasa_ocupacion se calcula correctamente"""
        # 30 ocupados / 50 totales = 0.6 = 60%
        assert recurso_disponible_basico.tasa_ocupacion == 0.6

    def test_recurso_sin_docente(self):
        """Verifica que docente es opcional"""
        recurso = RecursoDisponible(
            recurso_id="COM003",
            codigo_materia="3.4.069",
            nombre_materia="Test",
            ano_academico=2025,
            cuatrimestre=1,
            cupos_totales=50,
            horario_inicio="08:00",
            horario_fin="10:00",
        )
        assert recurso.docente_id is None
        assert recurso.docente_nombre is None

    def test_recurso_virtual(self):
        """Verifica que modalidad puede ser virtual"""
        recurso = RecursoDisponible(
            recurso_id="COM004",
            codigo_materia="3.4.069",
            nombre_materia="Test",
            ano_academico=2025,
            cuatrimestre=1,
            cupos_totales=100,
            modalidad="virtual",
            horario_inicio="18:00",
            horario_fin="20:00",
        )
        assert recurso.modalidad == "virtual"
