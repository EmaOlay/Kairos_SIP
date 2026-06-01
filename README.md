# Kairos - Motor de Analitica Prescriptiva

## Descripcion
Kairos es un MVP de motor de analitica prescriptiva disenado para optimizar la oferta academica en universidades. 
El sistema procesa trayectorias estudiantiles y reglas curriculares para prescribir la apertura optima de comisiones, balanceando la tasa de graduacion con la eficiencia operativa.

## Como levantarlo (Con Docker - ¡La forma facil!)

Tenes dos opciones segun que quieras hacer:

### 1. La Posta: Dashboard Interactivo + API
Para levantar todo el boliche (Backend FastAPI + Frontend React):
```bash
docker-compose up --build
```
- **Dashboard**: `http://localhost:8080`
- **API (Swagger/Docs)**: `http://localhost:8000/docs`

### 2. La Demo: Script de Validacion UADE
Si solo queres ver en la consola como el motor mastica el plan real de UADE (52 materias):
```bash
docker-compose -f docker-compose.demo.yml up --build
```

---

## Base de Datos (RF-008)

El stack levanta un PostgreSQL 16 (`kairos-db`) con un volumen persistente.
La API se conecta via `DATABASE_URL` (default: `postgresql+psycopg://kairos:kairos@kairos-db:5432/kairos`).

### Aplicar migraciones
```bash
docker-compose run --rm kairos-api alembic upgrade head
```

### Cargar el plan UADE en la DB (seed)
```bash
docker-compose run --rm kairos-api python scripts/seed_db.py
```

### Crear una nueva migracion
```bash
docker-compose run --rm kairos-api alembic revision --autogenerate -m "descripcion"
```

---

## Estado del Proyecto

### Completado
- [x] **Core Prescriptivo**: Motor basado en grafos (NetworkX) con analisis de demanda y correlatividades.
- [x] **Deteccion de Ciclos**: Validacion logica de planes de estudio para evitar rulos infinitos.
- [x] **ETL Robusto**: Ingesta de JSON/CSV con reportes detallados y agrupacion de errores.
- [x] **API REST**: Backend con FastAPI (Endpoints para procesar demanda y obtener grafos).
- [x] **Dashboard Moderno**: Frontend en React + Vite + Vis.js con estetica "Modern Tech Dark".
- [x] **Datos Reales**: Validado con el plan 1621 de Ingenieria en Informatica de UADE.
- [x] **Dockerizacion**: Ambientes listos para produccion y demo.

### Pendientes

#### Prioridad Media
- [ ] **Frontend**: Panel interactivo para carga de archivos (actualmente se suben via API).
- [ ] **Data**: Generar sample CSVs para recursos (comisiones) disponibles.

#### Prioridad Baja
- [ ] **Optimizacion avanzada**: Implementar pesos configurables (70% grad, 30% eficiencia).
- [ ] **Simulaciones What-if**: Predecir impacto de cambios en el plan de estudios.

## Stack Tecnologico
- **Backend**: Python 3.11, FastAPI, Pandas, NetworkX.
- **Frontend**: React 18, TypeScript, Vite, Vis-network.
- **DevOps**: Docker & Docker Compose.

## Estructura del Proyecto
```
kairos_sip/
 ├── src/kairos/       # Backend Core & API
 ├── frontend/         # Dashboard React
 ├── scripts/          # Scripts de utilidad y demo
 ├── tests/            # Suite de tests (+70 casos)
 ├── data/             # Datasets de prueba
 └── config/           # Configuracion del motor
```

## Licencia
TBD
