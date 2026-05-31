# Kairos Dashboard

Interfaz moderna para el Motor de Analítica Prescriptiva Kairos.

## Requisitos
- Node.js 18+
- Backend de Kairos corriendo en `localhost:8000`

## Instalación
```bash
npm install
```

## Desarrollo
```bash
npm run dev
```

## Estructura
- `src/components/Dashboard`: Lógica principal y Layout.
- `src/components/Graph`: Visualización de grafos con Vis.js.
- `src/components/Prescriptions`: Listado de decisiones de apertura.
- `src/services`: Comunicación con FastAPI.
- `src/styles`: Temas y variables CSS (Modern Tech Dark).
