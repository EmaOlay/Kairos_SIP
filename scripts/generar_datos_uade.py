"""
Generador de datos sinteticos realistas para Kairos

Este script genera trayectorias de estudiantes basadas en el plan real de UADE
para probar el motor de optimizacion con volumen y casos de borde.
"""

import json
import random
import pandas as pd
from pathlib import Path

def generar_datos_prueba(plan_path: Path, num_estudiantes: int = 100):
    with open(plan_path, "r", encoding="utf-8") as f:
        plan_raw = json.load(f)

    materias = plan_raw["materias"]
    plan_id = plan_raw["plan"]
    
    estudiantes = []
    registros = []
    
    # Perfiles de estudiantes
    perfiles = [
        {"nombre": "aplicado", "prob_aprobar": 0.9, "avance_promedio": 0.8},
        {"nombre": "promedio", "prob_aprobar": 0.7, "avance_promedio": 0.5},
        {"nombre": "recursante", "prob_aprobar": 0.4, "avance_promedio": 0.3},
    ]

    for i in range(num_estudiantes):
        est_id = f"EST{i:04d}"
        perfil = random.choice(perfiles)
        ano_ingreso = random.randint(2018, 2024)
        
        estudiantes.append({
            "estudiante_id": est_id,
            "codigo_carrera": "ING_INF",
            "plan_estudio_id": plan_id,
            "ano_ingreso": ano_ingreso
        })
        
        # Simular avance segun ano de ingreso
        anos_cursados = 2025 - ano_ingreso
        materias_disponibles = [m for m in materias if m["año"] <= anos_cursados + 1]
        
        for m in materias_disponibles:
            # Si es de un año muy avanzado para su ingreso, saltear con probabilidad
            if m["año"] > anos_cursados:
                if random.random() > 0.2: continue
            
            # Decidir estado
            r = random.random()
            if r < perfil["prob_aprobar"]:
                estado = "aprobada"
                calificacion = random.uniform(4, 10)
            elif r < 0.8:
                estado = "regular"
                calificacion = None
            else:
                estado = "pendiente"
                continue
                
            registros.append({
                "estudiante_id": est_id,
                "codigo_materia": m["codigo"],
                "nombre_materia": m["nombre"],
                "estado": estado,
                "ano_academico": random.randint(ano_ingreso, 2024),
                "cuatrimestre": random.choice([1, 2]),
                "calificacion": round(calificacion, 2) if calificacion else None
            })

    # Guardar CSVs
    output_dir = Path("data/raw")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    pd.DataFrame(estudiantes).to_csv(output_dir / "estudiantes_uade.csv", index=False)
    pd.DataFrame(registros).to_csv(output_dir / "registros_uade.csv", index=False)
    
    print(f"¡Listo! Se generaron {num_estudiantes} estudiantes con {len(registros)} registros.")

if __name__ == "__main__":
    generar_datos_prueba(Path("plan_estudio_ing_informatica.json"))
