import pandas as pd
import json
from pathlib import Path

def exportar_a_json_frontend():
    raw_dir = Path("data/raw")
    
    # Cargar los CSVs que generamos antes
    try:
        df_est = pd.read_csv(raw_dir / "estudiantes_uade.csv")
        df_reg = pd.read_csv(raw_dir / "registros_uade.csv")
        
        # Consolidar registros en estudiantes
        estudiantes_list = []
        for _, row in df_est.iterrows():
            est_id = row["estudiante_id"]
            reg_est = df_reg[df_reg["estudiante_id"] == est_id].to_dict('records')
            
            # Limpiar NaNs para que el JSON sea valido
            for r in reg_est:
                for k, v in r.items():
                    if pd.isna(v): r[k] = None

            estudiantes_list.append({
                "estudiante_id": str(est_id),
                "codigo_carrera": str(row["codigo_carrera"]),
                "plan_estudio_id": str(row["plan_estudio_id"]),
                "ano_ingreso": int(row["ano_ingreso"]),
                "registros_trayectoria": reg_est
            })
            
        # Guardar el JSON consolidado
        with open(raw_dir / "estudiantes_uade.json", "w", encoding="utf-8") as f:
            json.dump(estudiantes_list, f, indent=2)
            
        print(f"¡Listo! Se exportaron {len(estudiantes_list)} estudiantes a data/raw/estudiantes_uade.json")
        
    except FileNotFoundError:
        print("Error: No se encontraron los CSVs en data/raw. Corre primero scripts/generar_datos_uade.py")

if __name__ == "__main__":
    exportar_a_json_frontend()
