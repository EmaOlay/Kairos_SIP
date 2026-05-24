# Kairós - Motor de Analítica Prescriptiva

## Descripción

Kairós es un MVP de motor de analítica prescriptiva diseñado para optimizar la oferta académica en universidades.

El sistema procesa trayectorias estudiantiles y reglas curriculares para prescribir automáticamente la apertura óptima de comisiones, cupos y horarios, balanceando la tasa de graduación con la eficiencia operativa institucional.

## Stack Tecnológico

- **Lenguaje**: Python 3.11+
- **Procesamiento y ETL**: Pandas / Polars
- **Modelado de Grafos**: NetworkX
- **Infraestructura**: Docker

## Estructura del Proyecto

```
kairos_sip/
├── src/kairos/          # Código fuente principal
│   ├── core/            # Motor de optimización
│   ├── etl/             # Módulo de ingesta
│   ├── schemas/         # Esquemas de datos
│   └── utils/           # Utilidades
├── tests/               # Suite de tests
├── data/                # Datasets (raw, processed)
├── docker/              # Configuración Docker
├── config/              # Archivos de configuración
└── docs/                # Documentación técnica
```

## Inicio Rápido

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

### 1. Esquema de Datos Genérico
- `EstudianteTrayectoria`: Historial académico del estudiante
- `PlanEstudio`: Estructura curricular y correlatividades
- `RecursoDisponible`: Capacidades operativas (comisiones, horarios, docentes)

### 2. Módulo ETL
Ingesta, validación y limpieza de datasets desde archivos planos anonimizados.

### 3. Motor Core (KairosOptimizer)
Procesamiento del grafo de correlatividades y algoritmo de optimización prescriptiva.

## Próximas Etapas

- [ ] Implementar esquema de datos con Pydantic
- [ ] Desarrollar módulo ETL con validación robusta
- [ ] Construir clase KairosOptimizer con grafo de NetworkX
- [ ] Dockerizar la aplicación
- [ ] Desarrollar suite de tests

## Licencia

TBD
