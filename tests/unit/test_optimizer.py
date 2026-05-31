"""
Tests unitarios para kairos.core.optimizer
"""

import pytest
from kairos.core.optimizer import KairosOptimizer
from kairos.schemas.data_models import (
    EstadoMateria,
    RegistroTrayectoria,
    EstudianteTrayectoria,
    Materia,
    PlanEstudio,
    ConfiguracionKairos,
)


class TestKairosOptimizerInit:
    """Tests para inicializacion del optimizer"""

    def test_inicializacion_basica(self, plan_estudio_minimo):
        """Verifica que optimizer se inicializa correctamente"""
        optimizer = KairosOptimizer(plan_estudio_minimo)
        assert optimizer.plan == plan_estudio_minimo
        assert isinstance(optimizer.config, ConfiguracionKairos)

    def test_inicializacion_con_config(self, plan_estudio_minimo):
        """Verifica que se puede pasar config personalizada"""
        config = ConfiguracionKairos(min_tasa_ocupacion=0.5)
        optimizer = KairosOptimizer(plan_estudio_minimo, config)
        assert optimizer.config.min_tasa_ocupacion == 0.5

    def test_grafo_inicializado(self, plan_estudio_minimo):
        """Verifica que el grafo se construye correctamente"""
        optimizer = KairosOptimizer(plan_estudio_minimo)
        # Debe tener 2 nodos (2 materias en el fixture)
        assert len(optimizer.grafo_correlativas.nodes) == 2
        # Debe tener 1 arista (3.4.069 -> 3.4.070)
        assert len(optimizer.grafo_correlativas.edges) == 1

    def test_grafo_correlatividades(self, plan_estudio_minimo):
        """Verifica que aristas reflejan correlatividades correctas"""
        optimizer = KairosOptimizer(plan_estudio_minimo)
        # Debe haber arista 3.4.069 -> 3.4.070
        assert optimizer.grafo_correlativas.has_edge("3.4.069", "3.4.070")


class TestAgregarEstudiantes:
    """Tests para agregar estudiantes"""

    def test_agregar_estudiante_individual(self, plan_estudio_minimo, estudiante_basico):
        """Verifica que se puede agregar un estudiante"""
        optimizer = KairosOptimizer(plan_estudio_minimo)
        optimizer.agregar_estudiante(estudiante_basico)
        assert "EST001" in optimizer.estudiantes
        assert len(optimizer.estudiantes) == 1

    def test_agregar_multiples_estudiantes(self, plan_estudio_minimo):
        """Verifica que se pueden agregar multiples estudiantes"""
        optimizer = KairosOptimizer(plan_estudio_minimo)

        est1 = EstudianteTrayectoria(
            estudiante_id="EST001",
            codigo_carrera="ING_INF",
            plan_estudio_id="1621",
            ano_ingreso=2023,
        )
        est2 = EstudianteTrayectoria(
            estudiante_id="EST002",
            codigo_carrera="ING_INF",
            plan_estudio_id="1621",
            ano_ingreso=2023,
        )

        optimizer.agregar_estudiantes({est1.estudiante_id: est1, est2.estudiante_id: est2})

        assert len(optimizer.estudiantes) == 2
        assert "EST001" in optimizer.estudiantes
        assert "EST002" in optimizer.estudiantes


class TestCalcularMateriasDisponibles:
    """Tests para calculo de materias disponibles"""

    def test_estudiante_sin_aprobaciones(self, plan_estudio_minimo):
        """Verifica que estudiante sin aprobaciones solo ve materias sin prereqs"""
        optimizer = KairosOptimizer(plan_estudio_minimo)

        estudiante = EstudianteTrayectoria(
            estudiante_id="EST001",
            codigo_carrera="ING_INF",
            plan_estudio_id="1621",
            ano_ingreso=2023,
        )

        disponibles = optimizer._calcular_materias_disponibles(estudiante)
        # Solo 3.4.069 sin prereqs, no 3.4.070 que requiere 3.4.069
        assert "3.4.069" in disponibles
        assert "3.4.070" not in disponibles

    def test_estudiante_con_aprobaciones(
        self, plan_estudio_minimo, registro_trayectoria_aprobada
    ):
        """Verifica que estudiante con prereqs aprobados ve materias dependientes"""
        optimizer = KairosOptimizer(plan_estudio_minimo)

        estudiante = EstudianteTrayectoria(
            estudiante_id="EST001",
            codigo_carrera="ING_INF",
            plan_estudio_id="1621",
            ano_ingreso=2023,
            registros_trayectoria=[registro_trayectoria_aprobada],
        )

        disponibles = optimizer._calcular_materias_disponibles(estudiante)
        # Ahora debe ver 3.4.070 porque 3.4.069 esta aprobada
        assert "3.4.070" in disponibles
        # 3.4.069 ya esta aprobada, no debe aparecer
        assert "3.4.069" not in disponibles

    def test_todas_aprobadas(self, plan_estudio_minimo):
        """Verifica que estudiante con todo aprobado no ve materias disponibles"""
        optimizer = KairosOptimizer(plan_estudio_minimo)

        registros = [
            RegistroTrayectoria(
                codigo_materia="3.4.069",
                nombre_materia="Fundamentos de Informatica",
                estado=EstadoMateria.APROBADA,
                ano_academico=2023,
                cuatrimestre=1,
                calificacion=8.0,
            ),
            RegistroTrayectoria(
                codigo_materia="3.4.070",
                nombre_materia="Estructura de Datos",
                estado=EstadoMateria.APROBADA,
                ano_academico=2023,
                cuatrimestre=2,
                calificacion=8.5,
            ),
        ]

        estudiante = EstudianteTrayectoria(
            estudiante_id="EST001",
            codigo_carrera="ING_INF",
            plan_estudio_id="1621",
            ano_ingreso=2023,
            registros_trayectoria=registros,
        )

        disponibles = optimizer._calcular_materias_disponibles(estudiante)
        # Nada disponible
        assert len(disponibles) == 0


class TestAnalizarDemanda:
    """Tests para analisis de demanda"""

    def test_demanda_vacia(self, plan_estudio_minimo):
        """Verifica que demanda es vacia sin estudiantes"""
        optimizer = KairosOptimizer(plan_estudio_minimo)
        demanda = optimizer.analizar_demanda()
        assert len(demanda) == 0

    def test_demanda_baja(self, plan_estudio_minimo):
        """Verifica que se calcula demanda correctamente"""
        optimizer = KairosOptimizer(plan_estudio_minimo)

        # Agregar 2 estudiantes sin nada aprobado
        for i in range(2):
            est = EstudianteTrayectoria(
                estudiante_id=f"EST{i:03d}",
                codigo_carrera="ING_INF",
                plan_estudio_id="1621",
                ano_ingreso=2023,
            )
            optimizer.agregar_estudiante(est)

        demanda = optimizer.analizar_demanda()

        # Ambos estudiantes necesitan 3.4.069 (sin prereqs)
        assert demanda.get("3.4.069") == 2
        # Ninguno necesita 3.4.070 (requiere prereq)
        assert demanda.get("3.4.070", 0) == 0

    def test_demanda_con_aprobaciones(self, plan_estudio_minimo):
        """Verifica que demanda cambia cuando hay aprobaciones"""
        optimizer = KairosOptimizer(plan_estudio_minimo)

        # Estudiante 1: sin nada
        est1 = EstudianteTrayectoria(
            estudiante_id="EST001",
            codigo_carrera="ING_INF",
            plan_estudio_id="1621",
            ano_ingreso=2023,
        )

        # Estudiante 2: con 3.4.069 aprobada
        est2 = EstudianteTrayectoria(
            estudiante_id="EST002",
            codigo_carrera="ING_INF",
            plan_estudio_id="1621",
            ano_ingreso=2023,
            registros_trayectoria=[
                RegistroTrayectoria(
                    codigo_materia="3.4.069",
                    nombre_materia="Fundamentos de Informatica",
                    estado=EstadoMateria.APROBADA,
                    ano_academico=2023,
                    cuatrimestre=1,
                    calificacion=8.0,
                )
            ],
        )

        optimizer.agregar_estudiantes({est1.estudiante_id: est1, est2.estudiante_id: est2})
        demanda = optimizer.analizar_demanda()

        # EST001 necesita 3.4.069, EST002 necesita 3.4.070
        assert demanda.get("3.4.069") == 1
        assert demanda.get("3.4.070") == 1


class TestPrescribirAperturas:
    """Tests para prescripcion de aperturas"""

    def test_prescripcion_sin_demanda(self, plan_estudio_minimo):
        """Verifica prescripciones sin estudiantes"""
        optimizer = KairosOptimizer(plan_estudio_minimo)
        prescripciones = optimizer.prescribir_aperturas()
        # Sin demanda, nada se abre
        assert all(p["decision"] == "NO ABRIR" for p in prescripciones.values())

    def test_prescripcion_baja_demanda(self, plan_estudio_minimo):
        """Verifica que baja demanda resulta en NO ABRIR"""
        optimizer = KairosOptimizer(plan_estudio_minimo)

        # Agregar 1 estudiante (demanda = 1)
        est = EstudianteTrayectoria(
            estudiante_id="EST001",
            codigo_carrera="ING_INF",
            plan_estudio_id="1621",
            ano_ingreso=2023,
        )
        optimizer.agregar_estudiante(est)

        prescripciones = optimizer.prescribir_aperturas()

        # Con config default: min_tasa = 0.6, max_cupos = 50
        # Minimo = 50 * 0.6 = 30 estudiantes
        # Con 1 estudiante no llega el minimo
        assert prescripciones["3.4.069"]["decision"] == "NO ABRIR"

    def test_prescripcion_alta_demanda(self, plan_estudio_minimo):
        """Verifica que alta demanda resulta en ABRIR"""
        optimizer = KairosOptimizer(plan_estudio_minimo)

        # Agregar 30 estudiantes
        for i in range(30):
            est = EstudianteTrayectoria(
                estudiante_id=f"EST{i:03d}",
                codigo_carrera="ING_INF",
                plan_estudio_id="1621",
                ano_ingreso=2023,
            )
            optimizer.agregar_estudiante(est)

        prescripciones = optimizer.prescribir_aperturas()

        # Con 30 estudiantes demandando 3.4.069, debe ABRIR
        assert prescripciones["3.4.069"]["decision"] == "ABRIR"
        assert prescripciones["3.4.069"]["demanda"] == 30

    def test_prescripcion_estructura(self, plan_estudio_minimo):
        """Verifica estructura de respuesta de prescripcion"""
        optimizer = KairosOptimizer(plan_estudio_minimo)

        prescripciones = optimizer.prescribir_aperturas()

        for codigo, prescripcion in prescripciones.items():
            assert "codigo" in prescripcion
            assert "nombre" in prescripcion
            assert "decision" in prescripcion
            assert "razon" in prescripcion
            assert "demanda" in prescripcion
            assert "estudiantes_demandantes" in prescripcion
            assert prescripcion["decision"] in ["ABRIR", "NO ABRIR"]


class TestConfiguracionPersonalizada:
    """Tests con configuraciones personalizadas"""

    def test_config_tasa_ocupacion_baja(self, plan_estudio_minimo):
        """Verifica que config personalizada afecta decisiones"""
        config = ConfiguracionKairos(min_tasa_ocupacion=0.2)
        optimizer = KairosOptimizer(plan_estudio_minimo, config)

        # Agregar solo 10 estudiantes
        for i in range(10):
            est = EstudianteTrayectoria(
                estudiante_id=f"EST{i:03d}",
                codigo_carrera="ING_INF",
                plan_estudio_id="1621",
                ano_ingreso=2023,
            )
            optimizer.agregar_estudiante(est)

        prescripciones = optimizer.prescribir_aperturas()

        # Con min_tasa = 0.2, minimo = 50 * 0.2 = 10 estudiantes
        # Con 10 estudiantes, debe ABRIR
        assert prescripciones["3.4.069"]["decision"] == "ABRIR"

    def test_config_cupos_maximos(self, plan_estudio_minimo):
        """Verifica que max_cupos_por_comision se respeta"""
        config = ConfiguracionKairos(max_cupos_por_comision=20)
        optimizer = KairosOptimizer(plan_estudio_minimo, config)

        # Agregar 12 estudiantes
        for i in range(12):
            est = EstudianteTrayectoria(
                estudiante_id=f"EST{i:03d}",
                codigo_carrera="ING_INF",
                plan_estudio_id="1621",
                ano_ingreso=2023,
            )
            optimizer.agregar_estudiante(est)

        prescripciones = optimizer.prescribir_aperturas()

        # Con max_cupos = 20, min_tasa = 0.6
        # Minimo = 20 * 0.6 = 12 estudiantes
        # Con 12 estudiantes, debe ABRIR
        assert prescripciones["3.4.069"]["decision"] == "ABRIR"


class TestReportesYAnalisis:
    """Tests para reportes y analisis avanzados del optimizer"""

    def test_detectar_cuellos_de_botella(self, plan_estudio_minimo):
        """
        Vemos si detecta bien las materias que son un perno porque traban a medio mundo.
        """
        optimizer = KairosOptimizer(plan_estudio_minimo)
        
        # En el plan minimo, 3.4.069 tiene 1 dependiente (3.4.070)
        # Para que sea cuello de botella segun el codigo necesita >= 3
        cuellos = optimizer.detectar_cuellos_de_botella()
        assert len(cuellos) == 0 # El plan minimo es muy tranqui
        
        # Agregamos una materia que sea un cuello de botella en serio
        m1 = Materia(codigo="M1", nombre="Materia 1", ano=1, cuatrimestre=1)
        m2 = Materia(codigo="M2", nombre="Materia 2", ano=1, cuatrimestre=2, correlativas_anteriores=["M1"])
        m3 = Materia(codigo="M3", nombre="Materia 3", ano=1, cuatrimestre=2, correlativas_anteriores=["M1"])
        m4 = Materia(codigo="M4", nombre="Materia 4", ano=1, cuatrimestre=2, correlativas_anteriores=["M1"])
        
        plan_complejo = PlanEstudio(
            codigo_plan="TEST", nombre_carrera="Test", ano_vigencia=2021, duracion_anos=5,
            materias={"M1": m1, "M2": m2, "M3": m3, "M4": m4}
        )
        optimizer_complejo = KairosOptimizer(plan_complejo)
        cuellos = optimizer_complejo.detectar_cuellos_de_botella()
        
        assert len(cuellos) == 1
        assert cuellos[0]["codigo"] == "M1"
        assert cuellos[0]["materias_dependientes"] == 3

    def test_generar_grafo_visualizable(self, plan_estudio_minimo):
        """
        Chequeamos que el diccionario para la visualizacion no sea cualquier verdura.
        """
        optimizer = KairosOptimizer(plan_estudio_minimo)
        grafo_vis = optimizer.generar_grafo_visualizable()
        
        assert "nodes" in grafo_vis
        assert "edges" in grafo_vis
        assert len(grafo_vis["nodes"]) == 2
        assert len(grafo_vis["edges"]) == 1

    def test_reporte_prescriptivo_humano(self, plan_estudio_minimo):
        """
        Verificamos que el reporte para humanos tire algo con sentido.
        """
        optimizer = KairosOptimizer(plan_estudio_minimo)
        reporte = optimizer.reporte_prescriptivo()
        
        assert "REPORTE PRESCRIPTIVO DE KAIROS" in reporte
        assert "ANALISIS DE DEMANDA" in reporte
        assert "PRESCRIPCIONES DE APERTURA" in reporte

    def test_promedio_estudiante(self, plan_estudio_minimo, estudiante_basico):
        """
        Vemos si calcula bien el promedio de un pibe sin pifiarle a la cuenta.
        """
        optimizer = KairosOptimizer(plan_estudio_minimo)
        optimizer.agregar_estudiante(estudiante_basico)
        
        promedio = optimizer.calcular_promedio_estudiante("EST001")
        # En el fixture: 3.4.069 aprobada con 8.5. Solo una materia aprobada.
        assert promedio == 8.5
        
        assert optimizer.calcular_promedio_estudiante("PIBE_INEXISTENTE") is None

    def test_detectar_ciclos_en_plan(self):
        """
        Ojo con los planes circulares, que no se nos rompa el motor si un plan es un rulo.
        """
        m1 = Materia(codigo="M1", nombre="M1", ano=1, cuatrimestre=1, correlativas_anteriores=["M2"])
        m2 = Materia(codigo="M2", nombre="M2", ano=1, cuatrimestre=2, correlativas_anteriores=["M1"])
        
        plan_con_ciclo = PlanEstudio(
            codigo_plan="CICLO", nombre_carrera="Test", ano_vigencia=2021, duracion_anos=5,
            materias={"M1": m1, "M2": m2}
        )
        
        # El optimizer deberia chillar o al menos detectar que hay un ciclo
        optimizer = KairosOptimizer(plan_con_ciclo)
        assert optimizer.tiene_ciclos() is True
