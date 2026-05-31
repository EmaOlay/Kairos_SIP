"""
Script de ejemplo: Demostracion de Kairos

Carga datos de ejemplo, ejecuta el motor de optimizacion
y genera prescripciones.
"""

import json
from pathlib import Path

from kairos.schemas.data_models import (
    EstudianteTrayectoria,
    RegistroTrayectoria,
    PlanEstudio,
    EstadoMateria,
    ConfiguracionKairos,
)
from kairos.etl.ingester import DataIngester
from kairos.core.optimizer import KairosOptimizer
from kairos.utils import ConfigLoader


def crear_estudiantes_ejemplo() -> dict:
    """Crea algunos estudiantes de ejemplo para demo"""
    
    estudiantes = {}
    
    # Estudiante 1: En 2do ano, algunas materias aprobadas
    est1 = EstudianteTrayectoria(
        estudiante_id="EST001",
        codigo_carrera="ING_INF",
        plan_estudio_id="1621",
        ano_ingreso=2023,
        registros_trayectoria=[
            # Ano 1, Cuatrimestre 1 - Aprobadas
            RegistroTrayectoria(
                codigo_materia="3.4.069",
                nombre_materia="Fundamentos de Informatica",
                estado=EstadoMateria.APROBADA,
                ano_academico=2023,
                cuatrimestre=1,
                calificacion=7.5,
            ),
            RegistroTrayectoria(
                codigo_materia="3.4.164",
                nombre_materia="Sistemas de Informacion I",
                estado=EstadoMateria.APROBADA,
                ano_academico=2023,
                cuatrimestre=1,
                calificacion=8.0,
            ),
            RegistroTrayectoria(
                codigo_materia="2.1.002",
                nombre_materia="Pensamiento Critico y Comunicacion",
                estado=EstadoMateria.APROBADA,
                ano_academico=2023,
                cuatrimestre=1,
                calificacion=7.0,
            ),
            # Ano 1, Cuatrimestre 2 - Aprobadas
            RegistroTrayectoria(
                codigo_materia="3.4.071",
                nombre_materia="Programacion I",
                estado=EstadoMateria.APROBADA,
                ano_academico=2023,
                cuatrimestre=2,
                calificacion=8.5,
            ),
        ]
    )
    estudiantes[est1.estudiante_id] = est1
    
    # Estudiante 2: Mas adelantado
    est2 = EstudianteTrayectoria(
        estudiante_id="EST002",
        codigo_carrera="ING_INF",
        plan_estudio_id="1621",
        ano_ingreso=2022,
        registros_trayectoria=[
            # Todas las del ano 1 aprobadas
            RegistroTrayectoria(
                codigo_materia="3.4.069",
                nombre_materia="Fundamentos de Informatica",
                estado=EstadoMateria.APROBADA,
                ano_academico=2022,
                cuatrimestre=1,
                calificacion=8.0,
            ),
            RegistroTrayectoria(
                codigo_materia="3.4.164",
                nombre_materia="Sistemas de Informacion I",
                estado=EstadoMateria.APROBADA,
                ano_academico=2022,
                cuatrimestre=1,
                calificacion=7.5,
            ),
            RegistroTrayectoria(
                codigo_materia="2.1.002",
                nombre_materia="Pensamiento Critico y Comunicacion",
                estado=EstadoMateria.APROBADA,
                ano_academico=2022,
                cuatrimestre=1,
                calificacion=7.0,
            ),
            RegistroTrayectoria(
                codigo_materia="3.4.071",
                nombre_materia="Programacion I",
                estado=EstadoMateria.APROBADA,
                ano_academico=2022,
                cuatrimestre=2,
                calificacion=9.0,
            ),
            RegistroTrayectoria(
                codigo_materia="3.3.121",
                nombre_materia="Sistemas de Representacion",
                estado=EstadoMateria.APROBADA,
                ano_academico=2022,
                cuatrimestre=2,
                calificacion=7.0,
            ),
        ]
    )
    estudiantes[est2.estudiante_id] = est2
    
    return estudiantes


def crear_estudiantes_masivos(cantidad: int, ano_base: int = 2024) -> dict:
    """
    Crea una cantidad masiva de estudiantes con estado avanzado.
    
    Simula una cohorte completa que ha completado el primer ano.
    """
    estudiantes = {}
    
    # Materias aprobadas del ano 1 (basicas)
    materias_ano1 = [
        ("3.4.069", "Fundamentos de Informatica", 7.5),
        ("3.4.164", "Sistemas de Informacion I", 8.0),
        ("2.1.002", "Pensamiento Critico y Comunicacion", 7.0),
        ("3.4.071", "Programacion I", 8.5),
        ("3.3.121", "Sistemas de Representacion", 7.8),
    ]
    
    for i in range(1, cantidad + 1):
        est_id = f"EST{i:04d}"
        registros = []
        
        for codigo, nombre, calif in materias_ano1:
            registros.append(
                RegistroTrayectoria(
                    codigo_materia=codigo,
                    nombre_materia=nombre,
                    estado=EstadoMateria.APROBADA,
                    ano_academico=ano_base,
                    cuatrimestre=1,
                    calificacion=calif + (i % 3) * 0.3,  # Variacion leve
                )
            )
        
        estudiante = EstudianteTrayectoria(
            estudiante_id=est_id,
            codigo_carrera="ING_INF",
            plan_estudio_id="1621",
            ano_ingreso=ano_base,
            registros_trayectoria=registros,
        )
        estudiantes[est_id] = estudiante
    
    return estudiantes


def ejecutar_escenario(nombre: str, plan: PlanEstudio, estudiantes: dict, config: ConfiguracionKairos) -> dict:
    """
    Ejecuta un escenario completo de optimizacion.
    
    Retorna diccionario con estadisticas del escenario.
    """
    print("\n" + "-"*70)
    print(f"ESCENARIO: {nombre}")
    print(f"Estudiantes: {len(estudiantes)}")
    print("-"*70 + "\n")
    
    optimizer = KairosOptimizer(plan, config=config)
    optimizer.agregar_estudiantes(estudiantes)
    
    # Analizar demanda
    demanda = optimizer.analizar_demanda()
    print(f"Total de materias con demanda: {len(demanda)}")
    print(f"Total de inscripciones demandadas: {sum(demanda.values())}\n")
    
    # Generar prescripciones
    prescripciones = optimizer.prescribir_aperturas()
    a_abrir = [p for p in prescripciones.values() if p["decision"] == "ABRIR"]
    no_abrir = [p for p in prescripciones.values() if p["decision"] == "NO ABRIR"]
    
    print(f"Prescripciones:")
    print(f"  - A ABRIR: {len(a_abrir)}")
    for p in a_abrir[:5]:
        print(f"    * {p['codigo']}: {p['nombre']} ({p['demanda']} estudiantes)")
    if len(a_abrir) > 5:
        print(f"    ... y {len(a_abrir) - 5} mas")
    
    print(f"  - NO ABRIR: {len(no_abrir)}")
    for p in no_abrir[:3]:
        print(f"    * {p['codigo']}: {p['nombre']} ({p['demanda']} estudiantes)")
    if len(no_abrir) > 3:
        print(f"    ... y {len(no_abrir) - 3} mas")
    
    # Cuellos de botella
    cuellos = optimizer.detectar_cuellos_de_botella()
    if cuellos:
        print(f"\nCuellos de botella detectados: {len(cuellos)}")
        for cuello in cuellos[:3]:
            print(f"  * {cuello['codigo']}: {cuello['materias_dependientes']} dependientes")
    
    return {
        "nombre": nombre,
        "total_estudiantes": len(estudiantes),
        "total_demanda": sum(demanda.values()),
        "materias_con_demanda": len(demanda),
        "a_abrir": len(a_abrir),
        "no_abrir": len(no_abrir),
        "prescripciones": prescripciones,
    }


def main():
    print("\n" + "="*70)
    print("DEMOSTRACION: Kairos - Motor de Analitica Prescriptiva")
    print("="*70 + "\n")
    
    # Cargar configuracion desde JSON
    print("[*] Cargando configuracion...")
    try:
        config_dict = ConfigLoader.obtener_kairos_config()
        config = ConfiguracionKairos(**config_dict)
        print(f"    OK - Config: ocupacion={config.min_tasa_ocupacion}, pesos=({config.weight_tasa_graduacion}, {config.weight_eficiencia_operativa})\n")
    except Exception as e:
        print(f"    [!] No se cargo config personalizada, usando defaults: {e}\n")
        config = ConfiguracionKairos()
    
    # 1. Cargar plan de estudio
    print("1. Cargando plan de estudio...")
    ingester = DataIngester()
    
    try:
        plan = ingester.cargar_plan_estudio(
            Path("data/raw/plan_estudio_ing_informatica.json")
        )
        print(f"    Cargado: {plan.nombre_carrera} ({len(plan.materias)} materias)\n")
    except FileNotFoundError:
        print("     Archivo de plan no encontrado. Creando plan de ejemplo...\n")
        # Crear plan minimo para demo
        from kairos.schemas.data_models import Materia
        
        materias = {
            "3.4.069": Materia(codigo="3.4.069", nombre="Fundamentos de Informatica", 
                              ano=1, cuatrimestre=1),
            "3.4.164": Materia(codigo="3.4.164", nombre="Sistemas de Informacion I",
                              ano=1, cuatrimestre=1),
            "2.1.002": Materia(codigo="2.1.002", nombre="Pensamiento Critico y Comunicacion",
                              ano=1, cuatrimestre=1),
            "3.4.043": Materia(codigo="3.4.043", nombre="Teoria de Sistemas",
                              ano=1, cuatrimestre=1),
            "3.1.050": Materia(codigo="3.1.050", nombre="Elementos de Algebra y Geometria",
                              ano=1, cuatrimestre=1),
            "3.4.071": Materia(codigo="3.4.071", nombre="Programacion I",
                              ano=1, cuatrimestre=2),
            "3.1.024": Materia(codigo="3.1.024", nombre="Matematica Discreta",
                              ano=1, cuatrimestre=2),
            "3.3.121": Materia(codigo="3.3.121", nombre="Sistemas de Representacion",
                              ano=1, cuatrimestre=2),
            "3.2.178": Materia(codigo="3.2.178", nombre="Fundamentos de Quimica",
                              ano=1, cuatrimestre=2),
            "3.4.072": Materia(codigo="3.4.072", nombre="Arquitectura de Computadores",
                              ano=1, cuatrimestre=2),
        }
        
        plan = PlanEstudio(
            codigo_plan="1621",
            nombre_carrera="Ingenieria en Informatica",
            ano_vigencia=2021,
            duracion_anos=5,
            materias=materias,
        )
        print(f"    Plan de ejemplo creado ({len(materias)} materias)\n")
    
    # 2. Ejecutar multiples escenarios
    print("\n" + "="*70)
    print("EJECUCION DE ESCENARIOS")
    print("="*70)
    
    resultados = []
    
    # Escenario 1: Pocos estudiantes (sin aperturas esperadas)
    est_pocos = crear_estudiantes_ejemplo()
    resultado1 = ejecutar_escenario(
        "Escenario 1: Baja demanda (2 estudiantes)",
        plan,
        est_pocos,
        config
    )
    resultados.append(resultado1)
    
    # Escenario 2: Muchos estudiantes (con aperturas esperadas)
    est_muchos = crear_estudiantes_masivos(35)
    resultado2 = ejecutar_escenario(
        "Escenario 2: Alta demanda (35 estudiantes)",
        plan,
        est_muchos,
        config
    )
    resultados.append(resultado2)
    
    # Escenario 3: Cohorte mixta (estudiantes en diferentes etapas)
    est_mixtos = crear_estudiantes_ejemplo()
    est_mixtos.update(crear_estudiantes_masivos(40, ano_base=2023))
    resultado3 = ejecutar_escenario(
        "Escenario 3: Demanda mixta (42 estudiantes)",
        plan,
        est_mixtos,
        config
    )
    resultados.append(resultado3)
    
    # 3. Resumen comparativo
    print("\n" + "="*70)
    print("RESUMEN COMPARATIVO")
    print("="*70 + "\n")
    
    print(f"{'Escenario':<35} {'Estuds':<10} {'Demanda':<10} {'ABRIR':<10} {'NO ABRIR':<10}")
    print("-"*75)
    
    for r in resultados:
        print(
            f"{r['nombre']:<35} "
            f"{r['total_estudiantes']:<10} "
            f"{r['total_demanda']:<10} "
            f"{r['a_abrir']:<10} "
            f"{r['no_abrir']:<10}"
        )
    
    print("\n" + "="*70)
    print("CONCLUSIONES")
    print("="*70)
    
    print("""
Con baja demanda (2 estudiantes): No se abren comisiones.
Razon: Demanda < 30 estudiantes minimos (config: 50 cupos * 0.6 ocupacion).

Con alta demanda (35 estudiantes): Se abren comisiones que alcanzan el umbral.
Razon: Suficientes estudiantes para justificar costos operativos.

Con demanda mixta (42 estudiantes): Aperturas estrategicas basadas en
demanda acumulada y correlativas.

El motor optimiza balanceando tasa de graduacion (70%) vs
eficiencia operativa (30%), respetando restricciones minimas.
    """)


if __name__ == "__main__":
    main()
