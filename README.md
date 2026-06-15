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

## Autenticación y roles

A partir de la versión actual, el dashboard requiere iniciar sesión antes de
acceder al resto de la aplicación. La autenticación se realiza con usuario y
contraseña almacenados en la base de datos, y la sesión se mantiene mediante
un token JWT firmado.

### Roles soportados

- **Docente Funcional** (`docente_funcional`)
- **Director de Departamento** (`director_departamento`)
- **Decano** (`decano`)

### Usuarios de prueba (seed)

La migración `0003_usuarios_auth` crea automáticamente tres cuentas de
demostración. La contraseña inicial coincide con el nombre de usuario y
debe rotarse antes de cualquier despliegue productivo.

| Usuario     | Contraseña  | Rol                       |
|-------------|-------------|---------------------------|
| `docente1`  | `docente1`  | Docente Funcional         |
| `director1` | `director1` | Director de Departamento  |
| `decano1`   | `decano1`   | Decano                    |

### Endpoints expuestos

| Método | Ruta                      | Acceso                        | Descripción                                  |
|--------|---------------------------|-------------------------------|----------------------------------------------|
| POST   | `/api/v1/auth/login`      | Público                       | Devuelve un token JWT y los datos del usuario. |
| GET    | `/api/v1/auth/me`         | Cualquier usuario autenticado | Datos del usuario actual.                    |
| GET    | `/api/v1/users`           | Solo rol `decano`             | Lista todos los usuarios del sistema.        |
| POST   | `/api/v1/users`           | Solo rol `decano`             | Crea un nuevo usuario.                       |

### Variables de entorno relevantes

- `KAIROS_JWT_SECRET`: clave de firma del token JWT. **Obligatoria** en
  cualquier entorno distinto de desarrollo. Si falta y `KAIROS_ENV` no es
  `development`, `dev`, `test` o `testing`, la API no inicia.
- `KAIROS_ENV`: entorno de ejecución (`development`, `production`, etc.).
- `KAIROS_CORS_ORIGINS`: lista de orígenes adicionales permitidos por CORS,
  separados por comas (los orígenes locales habituales ya están incluidos
  por defecto).

### Notas sobre el almacenamiento de contraseñas

Las contraseñas se almacenan utilizando SHA-256 con una sal aleatoria por
usuario, en formato `<sal>:<digest>`. Esta primera iteración prioriza la
simplicidad; para escenarios de producción se recomienda migrar a un
algoritmo específicamente diseñado para contraseñas, como bcrypt o Argon2.

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
- [x] **Panel de configuración (RF-003)**: pesos cascada/rentabilidad ajustables por slider, score mínimo y tope de comisiones desde la UI; endpoint `GET /config` para defaults.
- [x] **Scoring por materia + turno**: demanda splitteada por turno preferido del alumno; scoring combinando cascada transitiva e ingreso por alumno con normalización a escala comparable.
- [x] **Mapa de correlatividades en pestaña aparte**: layout en tabs con grafo agrupado por año (LR hierárquico).
- [x] **Justificación por prescripción**: columna Razón con el motivo de cada decisión (score ≥ mínimo, score bajo, tope presupuestario).
- [x] **Datos reales**: validado con el plan 1621 de Ingeniería en Informática de UADE.
- [x] **Dockerización**: entornos listos para desarrollo y demo.
- [x] **Autenticación con roles**: login con usuario y contraseña almacenados en la base, sesión vía JWT, tres roles (Docente Funcional, Director de Departamento, Decano), guard de acceso al dashboard y endpoint administrativo de gestión de usuarios restringido al rol Decano.

### Pendientes

#### Prioridad media
- [ ] **Datos**: generar datasets de ejemplo de recursos (comisiones disponibles).

#### Prioridad baja
- [ ] **Simulaciones What-if comparativas**: comparar 2 configuraciones lado a lado y diffear resultados (la simulación on-the-fly con sliders ya está hecha).

### Ideas para próximas iteraciones

Mejoras que extenderían el modelo de optimización para acercarlo a un escenario real de gestión académica:

#### Datos del estudiante
- [ ] **Estado financiero del alumno**: integrar cuotas pagas / morosidad. Despriorizar la demanda de alumnos no al día (no se inscriben efectivamente) o ponderarla por probabilidad de inscripción según historial de pago.
- [ ] **Riesgo de deserción**: marcar alumnos en zona de abandono (sin actividad N cuatrimestres, materias arrastradas, baja regularidad) y priorizar abrirles materias críticas como retención.
- [ ] **Preferencia horaria múltiple**: hoy cada alumno tiene un único `turno_preferido`. Modelarlo como ranking (1° elección, 2° elección, fallback) para distribuir mejor la demanda.

#### Recursos operativos
- [ ] **Capacidad de aulas**: cada turno tiene N aulas con M asientos. El motor debería respetar el techo de capacidad por turno y derivar overflow a otra franja.
- [ ] **Disponibilidad de profesores**: pool de docentes con materias que pueden dictar y disponibilidad por turno. No abrir comisiones que no tengan docente asignable.
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

## Stack tecnológico

- **Backend**: Python 3.11, FastAPI, Pandas, NetworkX, SQLAlchemy 2.0, Alembic.
- **Frontend**: React 18, TypeScript, Vite, Vis-network.
- **Base de datos**: PostgreSQL 16.
- **DevOps**: Docker y Docker Compose.

## Estructura del proyecto

```
kairos_sip/
 ├── src/kairos/                  # Backend (Python)
 │    ├── core/                   # Motor prescriptivo: KairosOptimizer, scoring, grafo de correlativas
 │    ├── api/                    # FastAPI app
 │    │    ├── main.py            # Entry point + CORS + routers
 │    │    ├── deps.py            # Dependencias inyectadas (sesión DB, etc.)
 │    │    ├── schemas/           # Modelos Pydantic de request/response (incluye auth)
 │    │    └── v1/endpoints/      # Endpoints REST (planes, estudiantes, optimizer, graph, auth, users)
 │    ├── core/
 │    │    └── auth.py            # Hashing, JWT y dependencias de autenticación / roles
 │    ├── db/                     # SQLAlchemy: modelos ORM, session, repositorios
 │    ├── etl/                    # Ingesta y validación de JSON/CSV (DataIngester)
 │    ├── schemas/                # Modelos de dominio Pydantic (Plan, Materia, Estudiante, Config)
 │    └── utils/                  # Helpers compartidos
 ├── alembic/                     # Migraciones de base de datos
 │    └── versions/               # Cada migración versionada
 ├── frontend/                    # Dashboard (React + TypeScript + Vite)
 │    └── src/
 │         ├── components/
 │         │    ├── Auth/         # Pantalla de login y guard de rutas protegidas
 │         │    ├── Dashboard/    # Layout principal, tabs, panel de configuración
 │         │    ├── Graph/        # Visualizador de correlativas (vis-network)
 │         │    └── Prescriptions/# Tabla de prescripciones rankeadas
 │         ├── context/           # AuthContext (sesión, token, hook useAuth)
 │         ├── services/          # Cliente HTTP del API (kairosService.ts, authService.ts)
 │         └── styles/            # Variables CSS globales
 ├── scripts/                     # Utilidades de línea de comandos
 │    ├── run_api.py              # Levantar API local sin Docker
 │    ├── seed_db.py              # Cargar plan + estudiantes UADE en la DB
 │    ├── ejemplo_demo.py         # Corrida end-to-end del motor en consola
 │    ├── validar_motor_real.py   # Validar el motor contra el plan UADE real
 │    ├── generar_datos_uade.py   # Generar dataset sintético de estudiantes
 │    ├── parser_correlativas.py  # Parsear el plan oficial a JSON
 │    └── exportar_json_frontend.py # Exportar fixtures para el front
 ├── tests/                       # Suite de tests (+70 casos: unitarios + integración)
 ├── data/                        # Datasets de prueba
 │    └── raw/                    # plan_uade_api.json, estudiantes_uade.json
 ├── config/                      # Configuración del motor (kairos_config.json)
 ├── docker/                      # Dockerfile del backend
 ├── docker-compose.yml           # Stack completo: db + api + frontend
 ├── docker-compose.demo.yml      # Demo en consola (motor sin UI)
 ├── alembic.ini                  # Config de migraciones
 ├── .env.example                 # Template de variables de entorno
 └── pyproject.toml               # Dependencias Python
```

## Licencia

Por definir.
