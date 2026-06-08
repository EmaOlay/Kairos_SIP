"""
Endpoints para la optimizacion prescriptiva

Aca esta la carne del asado. Recibimos la data, prendemos el motor
y devolvemos las prescripciones. 
"""

from fastapi import APIRouter, HTTPException
from kairos.core.optimizer import KairosOptimizer
from kairos.schemas.data_models import PlanEstudio, ConfiguracionKairos
from kairos.api.schemas.optimizer import RequestProcesamiento, ResponsePrescripcion

router = APIRouter()

@router.post("/process", response_model=ResponsePrescripcion)
async def procesar_demanda(request: RequestProcesamiento):
    """
    Toma el plan y los pibes, y te dice que comisiones abrir.
    Es el endpoint principal para el analisis prescriptivo.
    """
    try:
        # 1. Inicializar el motor
        optimizer = KairosOptimizer(request.plan, request.config)
        
        # 2. Cargar los datos
        for est in request.estudiantes:
            optimizer.agregar_estudiante(est)

        if request.recursos:
            optimizer.agregar_recursos(request.recursos)
        if request.aulas:
            optimizer.agregar_aulas(request.aulas)
        if request.docentes:
            optimizer.agregar_docentes(request.docentes)
        if request.historico:
            optimizer.agregar_historico(request.historico)

        # 3. Correr validaciones basicas del plan
        bardo_plan = optimizer.validar_caminos()
        if any("ciclos" in p.lower() for p in bardo_plan):
            raise HTTPException(
                status_code=400, 
                detail=f"El plan de estudio tiene ciclos, asi no se puede: {bardo_plan}"
            )

        # 4. Generar prescripciones
        prescripciones = optimizer.prescribir_aperturas()
        demanda = optimizer.analizar_demanda()
        cuellos = optimizer.detectar_cuellos_de_botella()

        # 5. Armar la respuesta
        resumen = optimizer.reporte_prescriptivo()
        metricas = optimizer.metricas_operativas(prescripciones)

        config_efectiva = request.config or ConfiguracionKairos()
        return ResponsePrescripcion(
            carrera=request.plan.nombre_carrera,
            prescripciones=prescripciones,
            cuellos_botella=cuellos,
            demanda_total=sum(demanda.values()),
            materias_con_demanda=len(demanda),
            resumen=resumen,
            metricas_operativas=metricas,
            config_usada={
                "weight_tasa_graduacion": config_efectiva.weight_tasa_graduacion,
                "weight_eficiencia_operativa": config_efectiva.weight_eficiencia_operativa,
                "min_tasa_ocupacion": config_efectiva.min_tasa_ocupacion,
                "max_cupos_por_comision": config_efectiva.max_cupos_por_comision,
                "max_comisiones_a_abrir": config_efectiva.max_comisiones_a_abrir,
            }
        )

    except Exception as e:
        # Si se rompe algo, no queremos que muera en silencio
        raise HTTPException(status_code=500, detail=f"Se armo bardo en el motor: {str(e)}")

@router.get("/config")
async def obtener_config():
    """Devuelve la configuracion default del motor para sincronizar con el frontend."""
    config = ConfiguracionKairos()
    return {
        "weight_tasa_graduacion": config.weight_tasa_graduacion,
        "weight_eficiencia_operativa": config.weight_eficiencia_operativa,
        "min_tasa_ocupacion": config.min_tasa_ocupacion,
        "max_cupos_por_comision": config.max_cupos_por_comision,
        "max_comisiones_a_abrir": config.max_comisiones_a_abrir,
    }

@router.post("/graph")
async def obtener_grafo(plan: PlanEstudio):
    """
    Te devuelve el grafo del plan listo para que lo dibujes en el front.
    Ideal para ver como estan conectadas las materias.
    """
    try:
        optimizer = KairosOptimizer(plan)
        return optimizer.generar_grafo_visualizable()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"No pudimos dibujar el grafo: {str(e)}")
