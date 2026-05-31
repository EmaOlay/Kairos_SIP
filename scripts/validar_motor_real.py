"""
Script de validacion del Motor Kairos con datos reales de UADE

Este script carga el plan de estudio completo de Ingenieria en Informatica,
ingesta los 100 estudiantes sinteticos generados y ejecuta el analisis
prescriptivo para ver que materias tienen mas demanda.
"""

from pathlib import Path
from kairos.etl.ingester import DataIngester
from kairos.core.optimizer import KairosOptimizer

def validar_motor_real():
    print("\n--- INICIANDO VALIDACION CON DATOS REALES UADE ---")
    
    # 1. Ingesta
    ingester = DataIngester()
    
    # Cargar Plan (Ojo: el JSON real tiene nombres de campos en español, el Ingester espera el schema)
    # Vamos a usar el cargador que ya tenemos
    try:
        # Nota: El archivo plan_estudio_ing_informatica.json usa "año" y "año_vigencia"
        # Nuestro schema usa "ano" y "ano_vigencia". El Ingester podria chillar.
        # Vamos a leerlo y fixear los keys al vuelo si hace falta.
        import json
        with open("plan_estudio_ing_informatica.json", "r", encoding="utf-8") as f:
            plan_data = json.load(f)
        
        # Mapeo de campos para que pydantic no se rompa
        plan_fixed = {
            "codigo_plan": plan_data["plan"],
            "nombre_carrera": plan_data["carrera"],
            "ano_vigencia": int(plan_data["año_vigencia"]),
            "duracion_anos": 5,
            "materias": {
                m["codigo"]: {
                    "codigo": m["codigo"],
                    "nombre": m["nombre"],
                    "ano": m["año"],
                    "cuatrimestre": m["cuatrimestre"],
                    "correlativas_anteriores": m["correlativas_anteriores"]
                } for m in plan_data["materias"]
            }
        }
        
        # Guardar temporalmente el fixed
        with open("data/raw/plan_uade_fixed.json", "w", encoding="utf-8") as f:
            json.dump(plan_fixed, f)
            
        ingester.cargar_plan_estudio(Path("data/raw/plan_uade_fixed.json"))
        ingester.cargar_trayectorias_estudiantes(Path("data/raw/estudiantes_uade.csv"))
        ingester.cargar_registros_trayectoria(Path("data/raw/registros_uade.csv"))
        
        valido, problemas = ingester.validar_integridad()
        if not valido:
            print(f"¡Atenti! Hubo mambos en la integridad:\n" + "\n".join(problemas[:5]))
            
        # 2. Optimizacion
        optimizer = KairosOptimizer(ingester.plan_estudio)
        optimizer.agregar_estudiantes(ingester.estudiantes)
        
        # Validar caminos del plan real
        bulla_plan = optimizer.validar_caminos()
        if bulla_plan:
            print(f"\nOjo con el plan de UADE, saltaron estas alertas:\n" + "\n".join(bulla_plan))
        else:
            print("\nEl plan de estudio esta impecable, sin ciclos ni cosas raras.")

        # 3. Reporte
        print("\nGenerando reporte prescriptivo basado en los 100 estudiantes...")
        print(optimizer.reporte_prescriptivo())
        
    except Exception as e:
        print(f"Se rompio todo cargando los datos reales: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    validar_motor_real()
