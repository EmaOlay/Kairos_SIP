# Kairos - Motor de Analitica Prescriptiva

## Descripcion
Kairos es un MVP de motor de analitica prescriptiva disenado para optimizar la oferta academica en universidades. 
El sistema procesa trayectorias estudiantiles y reglas curriculares para prescribir la apertura optima de comisiones, balanceando la tasa de graduacion con la eficiencia operativa.

## Configuracion (.env)

Las credenciales y la URL de la DB son configurables via variables de entorno.
Antes de levantar el stack, copia el template:

```bash
cp .env.example .env
```

El archivo `.env` esta gitignoreado (no se commitea). Edita los valores que
quieras cambiar (usuario/password/puerto de Postgres, `DATABASE_URL`, etc.).
Si no haces nada, `docker-compose` usa los defaults razonables del template
(usuario y password `kairos` para dev local).

> Cambia los defaults antes de cualquier deploy productivo. El `.env.example`
> es solo una plantilla con valores de desarrollo.

---

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

### Ideas para próximas iteraciones

Mejoras que extenderían el modelo de optimización para acercarlo a un escenario real de gestión académica:

#### Datos del estudiante
- [ ] **Estado financiero del alumno**: integrar cuotas pagas / morosidad. Despriorizar la demanda de alumnos no al día (no se inscriben efectivamente) o ponderarla por probabilidad de inscripción según historial de pago.
- [ ] **Probabilidad de aprobación**: usar el promedio académico y la dificultad histórica de la materia para estimar quién va a aprobar. Hoy todos cuentan como demanda válida con peso 1.
- [ ] **Riesgo de deserción**: marcar alumnos en zona de abandono (sin actividad N cuatrimestres, materias arrastradas, baja regularidad) y priorizar abrirles materias críticas como retención.
- [ ] **Preferencia horaria múltiple**: hoy cada alumno tiene un único `turno_preferido`. Modelarlo como ranking (1° elección, 2° elección, fallback) para distribuir mejor la demanda.

#### Recursos operativos
- [ ] **Capacidad de aulas**: cada turno tiene N aulas con M asientos. El motor debería respetar el techo de capacidad por turno y derivar overflow a otra franja.
- [ ] **Disponibilidad de profesores**: pool de docentes con materias que pueden dictar y disponibilidad por turno. No abrir comisiones que no tengan docente asignable.
- [ ] **Costos reales**: salario del profesor + costo del aula + servicios. Hoy la "rentabilidad" solo mira ingresos, no costos. Pasar a margen neto = ingreso − costo.
- [ ] **Carga horaria docente**: balancear horas asignadas para no sobrecargar profesores ni dejar vacantes.

#### Algoritmo
- [ ] **Solver de optimización**: reemplazar el ranking greedy por un MILP (PuLP / OR-Tools) cuando se sumen las restricciones de aulas y profesores. El greedy alcanza para dimensiones chicas, pero con N restricciones duras conviene un solver.
- [ ] **Restricciones de equidad (fairness)**: garantizar mínimo de comisiones por turno para no discriminar a alumnos que solo pueden cursar de mañana.
- [ ] **Aprendizaje de pesos**: entrenar los pesos `cascada` vs `rentabilidad` con datos históricos (qué comisiones efectivamente se llenaron y se sostuvieron) en vez de fijarlos a mano.
- [ ] **Análisis multi-cuatrimestre**: planificar 2-3 cuatrimestres hacia adelante, no solo el próximo. Permite anticipar cuellos de botella futuros.

#### UX / Producto
- [ ] **Comparador de escenarios**: simular dos configuraciones lado a lado y diffear resultados.
- [ ] **Histórico de prescripciones**: persistir cada corrida en la DB y mostrar evolución entre cuatrimestres.
- [ ] **Exportar a Excel/PDF**: para que el director comparta la propuesta con decanato.
- [ ] **Alertas tempranas**: detectar materias que van a saturar (demanda > capacidad proyectada) o quedar vacías antes de que pase.

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
