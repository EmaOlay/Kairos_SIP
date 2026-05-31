# Kairos - Motor de Analitica Prescriptiva

## Descripcion

Kairos es un MVP de motor de analitica prescriptiva disenado para optimizar la oferta academica en universidades.

El sistema procesa trayectorias estudiantiles y reglas curriculares para prescribir automaticamente la apertura optima de comisiones, cupos y horarios, balanceando la tasa de graduacion con la eficiencia operativa institucional.

## Stack Tecnologico

- **Lenguaje**: Python 3.11+
- **Procesamiento y ETL**: Pandas / Polars
- **Modelado de Grafos**: NetworkX
- **Infraestructura**: Docker

## Estructura del Proyecto

```
kairos_sip/
 src/kairos/          # Codigo fuente principal
    core/            # Motor de optimizacion
    etl/             # Modulo de ingesta
    schemas/         # Esquemas de datos
    utils/           # Utilidades
 tests/               # Suite de tests
 data/                # Datasets (raw, processed)
 docker/              # Configuracion Docker
 config/              # Archivos de configuracion
 docs/                # Documentacion tecnica
```

## Inicio Rapido

### Con Docker

```bash
docker-compose up --build
```

### Sin Docker (desarrollo local)

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Componentes Principales

### 1. Esquema de Datos Generico
- `EstudianteTrayectoria`: Historial academico del estudiante
- `PlanEstudio`: Estructura curricular y correlatividades
- `RecursoDisponible`: Capacidades operativas (comisiones, horarios, docentes)

### 2. Modulo ETL
Ingesta, validacion y limpieza de datasets desde archivos planos anonimizados.

### 3. Motor Core (KairosOptimizer)
Procesamiento del grafo de correlatividades y algoritmo de optimizacion prescriptiva.

## Estado del Proyecto

### Completado
- [x] Esquema de datos con Pydantic (EstudianteTrayectoria, PlanEstudio, etc.)
- [x] Configuracion centralizada en JSON (config/kairos_config.json)
- [x] Clase KairosOptimizer con analisis basico de demanda
- [x] Docker + docker-compose setup
- [x] Demo con 3 escenarios (baja/alta/mixta demanda)
- [x] Parser de correlatividades (scripts/parser_correlativas.py)
- [x] Modulo ETL inicial (ingester.py) con `validar_integridad()` completo
- [x] Suite de tests unitarios (Schemas, ETL, Core, Utils) con +60 casos
- [x] Deteccion de ciclos en el grafo de correlatividades

### Pendientes

#### Prioridad Alta (Proximas 2 sprints)
- [ ] **Manejo robusto de errores**: Refinar capturas y reportes en ETL
- [ ] **Tests de integracion**: Flujo completo desde CSV hasta Prescripcion
- [ ] **Grafo de correlatividades**:
  - [ ] Implementar correlativas_anteriores/posteriores correctamente (bidireccional)
  - [ ] Validacion de caminos validos

#### Prioridad Media (Siguientes 2 sprints)
- [ ] **API REST**:
  - [ ] Endpoint POST para procesar dataset
  - [ ] Endpoint GET para obtener prescripciones
  - [ ] Schemas de respuesta JSON
  - [ ] Manejo de errores HTTP
- [ ] **Datos reales**:
  - [ ] Cargar plan_estudio_ing_informatica.json completo (52 materias UADE)
  - [ ] Sample CSVs para trayectorias estudiantiles
  - [ ] Sample CSVs para recursos disponibles
- [ ] **Frontend básico**: Dashboard para visualizar prescripciones

#### Prioridad Baja (Futuros sprints)
- [ ] **Optimizacion avanzada**:
  - [ ] Implementar pesos diferenciados (70% grad, 30% eficiencia)
  - [ ] Algoritmo de balanceo de cargas entre comisiones
- [ ] **Análisis avanzado**:
  - [ ] Detectar cuellos de botella en cascada
  - [ ] Prediccion de retenciones
  - [ ] Simulaciones "what-if"
- [ ] **Performance**:
  - [ ] Indexacion de queries frecuentes
  - [ ] Cache de calculos intermedios
  - [ ] Benchmarks y profiling

## Proximas Etapas

Refinar el manejo de errores en el modulo ETL y comenzar con la implementacion 
de la **API REST** para exponer las funcionalidades del motor prescriptivo.
Seguir ampliando la cobertura de tests a medida que se agregan nuevas funcionalidades.

## Licencia

TBD
