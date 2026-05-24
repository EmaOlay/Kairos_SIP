"""
Script de ejemplo: Demostración de Kairós

Carga datos de ejemplo, ejecuta el motor de optimización
y genera prescripciones.
"""

import json
from pathlib import Path

from src.kairos.schemas.data_models import (
    EstudianteTrayectoria,
    RegistroTrayectoria,
    PlanEstudio,
    EstadoMateria,
)
from src.kairos.etl.ingester import DataIngester
from src.kairos.core.optimizer import KairosOptimizer


def crear_estudiantes_ejemplo() -> dict:
    """Crea algunos estudiantes de ejemplo para demo"""
    
    estudiantes = {}
    
    # Estudiante 1: En 2do año, algunas materias aprobadas
    est1 = EstudianteTrayectoria(
        estudiante_id="EST001",
        codigo_carrera="ING_INF",
        plan_estudio_id="1621",
        año_ingreso=2023,
        registros_trayectoria=[
            # Año 1, Cuatrimestre 1 - Aprobadas
            RegistroTrayectoria(
                codigo_materia="3.4.069",
                nombre_materia="Fundamentos de Informática",
                estado=EstadoMateria.APROBADA,
                año_academico=2023,
                cuatrimestre=1,
                calificacion=7.5,
            ),
            RegistroTrayectoria(
                codigo_materia="3.4.164",
                nombre_materia="Sistemas de Información I",
                estado=EstadoMateria.APROBADA,
                año_academico=2023,
                cuatrimestre=1,
                calificacion=8.0,
            ),
            RegistroTrayectoria(
                codigo_materia="2.1.002",
                nombre_materia="Pensamiento Crítico y Comunicación",
                estado=EstadoMateria.APROBADA,
                año_academico=2023,
                cuatrimestre=1,
                calificacion=7.0,
            ),
            # Año 1, Cuatrimestre 2 - Aprobadas
            RegistroTrayectoria(
                codigo_materia="3.4.071",
                nombre_materia="Programación I",
                estado=EstadoMateria.APROBADA,
                año_academico=2023,
                cuatrimestre=2,
                calificacion=8.5,
            ),
        ]
    )
    estudiantes[est1.estudiante_id] = est1
    
    # Estudiante 2: Más adelantado
    est2 = EstudianteTrayectoria(
        estudiante_id="EST002",
        codigo_carrera="ING_INF",
        plan_estudio_id="1621",
        año_ingreso=2022,
        registros_trayectoria=[
            # Todas las del año 1 aprobadas
            RegistroTrayectoria(
                codigo_materia="3.4.069",
                nombre_materia="Fundamentos de Informática",
                estado=EstadoMateria.APROBADA,
                año_academico=2022,
                cuatrimestre=1,
                calificacion=8.0,
            ),
            RegistroTrayectoria(
                codigo_materia="3.4.164",
                nombre_materia="Sistemas de Información I",
                estado=EstadoMateria.APROBADA,
                año_academico=2022,
                cuatrimestre=1,
                calificacion=7.5,
            ),
            RegistroTrayectoria(
                codigo_materia="2.1.002",
                nombre_materia="Pensamiento Crítico y Comunicación",
                estado=EstadoMateria.APROBADA,
                año_academico=2022,
                cuatrimestre=1,
                calificacion=7.0,
            ),
            RegistroTrayectoria(
                codigo_materia="3.4.071",
                nombre_materia="Programación I",
                estado=EstadoMateria.APROBADA,
                año_academico=2022,
                cuatrimestre=2,
                calificacion=9.0,
            ),
            RegistroTrayectoria(
                codigo_materia="3.3.121",
                nombre_materia="Sistemas de Representación",
                estado=EstadoMateria.APROBADA,
                año_academico=2022,
                cuatrimestre=2,
                calificacion=7.0,
            ),
        ]
    )
    estudiantes[est2.estudiante_id] = est2
    
    return estudiantes


def main():
    print("\n" + "="*70)
    print("DEMOSTRACIÓN: Kairós - Motor de Analítica Prescriptiva")
    print("="*70 + "\n")
    
    # 1. Cargar plan de estudio
    print("1️⃣  Cargando plan de estudio...")
    ingester = DataIngester()
    
    try:
        plan = ingester.cargar_plan_estudio(
            Path("data/raw/plan_estudio_ing_informatica.json")
        )
        print(f"   ✓ Cargado: {plan.nombre_carrera} ({len(plan.materias)} materias)\n")
    except FileNotFoundError:
        print("   ⚠️  Archivo de plan no encontrado. Creando plan de ejemplo...\n")
        # Crear plan mínimo para demo
        from src.kairos.schemas.data_models import Materia
        
        materias = {
            "3.4.069": Materia(codigo="3.4.069", nombre="Fundamentos de Informática", 
                              año=1, cuatrimestre=1),
            "3.4.164": Materia(codigo="3.4.164", nombre="Sistemas de Información I",
                              año=1, cuatrimestre=1),
            "2.1.002": Materia(codigo="2.1.002", nombre="Pensamiento Crítico y Comunicación",
                              año=1, cuatrimestre=1),
            "3.4.043": Materia(codigo="3.4.043", nombre="Teoría de Sistemas",
                              año=1, cuatrimestre=1),
            "3.1.050": Materia(codigo="3.1.050", nombre="Elementos de Álgebra y Geometría",
                              año=1, cuatrimestre=1),
            "3.4.071": Materia(codigo="3.4.071", nombre="Programación I",
                              año=1, cuatrimestre=2),
            "3.1.024": Materia(codigo="3.1.024", nombre="Matemática Discreta",
                              año=1, cuatrimestre=2),
            "3.3.121": Materia(codigo="3.3.121", nombre="Sistemas de Representación",
                              año=1, cuatrimestre=2),
            "3.2.178": Materia(codigo="3.2.178", nombre="Fundamentos de Química",
                              año=1, cuatrimestre=2),
            "3.4.072": Materia(codigo="3.4.072", nombre="Arquitectura de Computadores",
                              año=1, cuatrimestre=2),
        }
        
        plan = PlanEstudio(
            codigo_plan="1621",
            nombre_carrera="Ingeniería en Informática",
            año_vigencia=2021,
            duracion_años=5,
            materias=materias,
        )
        print(f"   ✓ Plan de ejemplo creado ({len(materias)} materias)\n")
    
    # 2. Crear estudiantes
    print("2️⃣  Cargando estudiantes...")
    estudiantes = crear_estudiantes_ejemplo()
    print(f"   ✓ {len(estudiantes)} estudiantes cargados\n")
    
    # 3. Inicializar motor
    print("3️⃣  Inicializando motor de optimización...")
    optimizer = KairosOptimizer(plan)
    optimizer.agregar_estudiantes(estudiantes)
    print("   ✓ Motor listo\n")
    
    # 4. Analizar demanda
    print("4️⃣  Analizando demanda...")
    demanda = optimizer.analizar_demanda()
    print(f"   ✓ Análisis completado\n")
    
    # 5. Generar prescripciones
    print("5️⃣  Generando prescripciones...")
    prescripciones = optimizer.prescribir_aperturas()
    print(f"   ✓ Prescripciones generadas\n")
    
    # 6. Detectar cuellos de botella
    print("6️⃣  Detectando cuellos de botella...")
    cuellos = optimizer.detectar_cuellos_de_botella()
    print(f"   ✓ Análisis completado\n")
    
    # 7. Reporte
    print(optimizer.reporte_prescriptivo())
    
    # Información detallada de estudiantes
    print("DETALLES DE ESTUDIANTES:")
    for est_id, est in estudiantes.items():
        aprobadas = len(est.materias_aprobadas)
        promedio = est.promedio_academico
        disponibles = optimizer._calcular_materias_disponibles(est)
        
        print(f"\n  {est_id}:")
        print(f"    Materias aprobadas: {aprobadas}")
        print(f"    Promedio: {promedio:.2f}" if promedio else "    Promedio: N/A")
        print(f"    Materias disponibles para cursar: {len(disponibles)}")
        if disponibles:
            print(f"    Códigos: {', '.join(sorted(disponibles)[:3])}...")


if __name__ == "__main__":
    main()
