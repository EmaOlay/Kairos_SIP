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
- [x] Modulo ETL inicial (ingester.py)

### Pendientes

#### Prioridad Alta (Proximas 2 sprints)
- [ ] **Tests unitarios**: Data models y validaciones
- [ ] **Tests unitarios**: Optimizer (demanda, prescripciones, correlativas)
- [ ] **Completar ETL**:
  - [ ] Terminar metodo `validar_integridad()` en ingester.py
  - [ ] Manejo robusto de errores y datos invalidos
  - [ ] Tests de integracion para loaders CSV/JSON
- [ ] **Grafo de correlatividades**:
  - [ ] Implementar correlativas_anteriores/posteriores correctamente
  - [ ] Detectar ciclos en el grafo
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

Comenzar con la suite de tests para validar funcionalidad existente,
seguido por completar el modulo ETL y exponerlo via API REST.

## Licencia

TBD
