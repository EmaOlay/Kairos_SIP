# Kairos — Motor de Analítica Prescriptiva

## Descripción

Kairos es un MVP de motor de analítica prescriptiva diseñado para optimizar la oferta académica en universidades. El sistema procesa trayectorias estudiantiles y reglas curriculares para prescribir la apertura óptima de comisiones, balanceando la tasa de graduación con la eficiencia operativa.

## Configuración (.env)

Las credenciales y la URL de la base de datos son configurables mediante variables de entorno. Antes de levantar el stack, copie el template:

```bash
cp .env.example .env
```

El archivo `.env` está incluido en `.gitignore` y no se versiona. Edite los valores que necesite (usuario, contraseña y puerto de PostgreSQL, `DATABASE_URL`, etc.). Si no realiza modificaciones, `docker-compose` utilizará los valores por defecto definidos en la plantilla (usuario y contraseña `kairos`, válidos solo para desarrollo local).

> Antes de cualquier despliegue productivo, modifique los valores por defecto. `.env.example` es únicamente una plantilla de desarrollo.

---

## Puesta en marcha con Docker

El proyecto ofrece dos modos de ejecución:

### 1. Stack completo: Dashboard interactivo + API

Levanta el backend (FastAPI) y el frontend (React):

```bash
docker-compose up --build
```

- **Dashboard**: `http://localhost:8080`
- **API (Swagger / Docs)**: `http://localhost:8000/docs`

### 2. Demo en consola: validación con el plan UADE

Ejecuta el script de validación contra el plan real de UADE (52 materias) e imprime el análisis en consola:

```bash
docker-compose -f docker-compose.demo.yml up --build
```

---

## Base de datos (RF-008)

El stack incluye un servicio PostgreSQL 16 (`kairos-db`) con volumen persistente. La API se conecta mediante `DATABASE_URL` (valor por defecto: `postgresql+psycopg://kairos:kairos@kairos-db:5432/kairos`).

### Aplicar migraciones

```bash
docker-compose run --rm kairos-api alembic upgrade head
```

### Cargar datos iniciales (plan UADE + estudiantes de prueba)

```bash
docker-compose run --rm kairos-api python scripts/seed_db.py
```

### Crear una nueva migración

```bash
docker-compose run --rm kairos-api alembic revision --autogenerate -m "descripcion"
```

---

## Estado del proyecto

### Completado
- [x] **Núcleo prescriptivo**: motor basado en grafos (NetworkX) con análisis de demanda y correlatividades.
- [x] **Detección de ciclos**: validación lógica de planes de estudio para evitar dependencias circulares.
- [x] **ETL**: ingesta de JSON y CSV con reportes detallados y agrupación de errores.
- [x] **API REST**: backend con FastAPI; endpoints para procesar demanda y obtener grafos.
- [x] **Dashboard**: frontend en React + Vite + Vis.js con estética "Modern Tech Dark".
- [x] **Persistencia (RF-008)**: PostgreSQL con SQLAlchemy 2.0 y migraciones gestionadas por Alembic.
- [x] **Integración DB ↔ Front (RF-010)**: el frontend consume planes y estudiantes desde la base; soporta ingesta de JSON desde la UI.
- [x] **Datos reales**: validado con el plan 1621 de Ingeniería en Informática de UADE.
- [x] **Dockerización**: entornos listos para desarrollo y demo.

### Pendientes

#### Prioridad media
- [ ] **Datos**: generar datasets de ejemplo de recursos (comisiones disponibles).

#### Prioridad baja
- [ ] **Optimización avanzada**: pesos configurables (70% graduación, 30% eficiencia) ajustables por contexto.
- [ ] **Simulaciones What-if**: predecir el impacto de cambios en el plan de estudios.

## Stack tecnológico

- **Backend**: Python 3.11, FastAPI, Pandas, NetworkX, SQLAlchemy 2.0, Alembic.
- **Frontend**: React 18, TypeScript, Vite, Vis-network.
- **Base de datos**: PostgreSQL 16.
- **DevOps**: Docker y Docker Compose.

## Estructura del proyecto

```
kairos_sip/
 ├── src/kairos/       # Backend: núcleo del motor + API
 ├── frontend/         # Dashboard en React
 ├── scripts/          # Scripts de utilidad (seeds, demos)
 ├── alembic/          # Migraciones de la base de datos
 ├── tests/            # Suite de tests (+70 casos)
 ├── data/             # Datasets de prueba
 └── config/           # Configuración del motor
```

## Licencia

Por definir.
