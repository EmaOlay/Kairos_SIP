import { getStoredToken } from './authService';

const API_BASE_URL = 'http://localhost:8000/api/v1';

function authHeaders(): Record<string, string> {
  const token = getStoredToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

export interface Plan {
  codigo_plan: string;
  nombre_carrera: string;
  ano_vigencia: number;
  duracion_anos: number;
  materias: Record<string, any>;
}

export interface Student {
  estudiante_id: string;
  codigo_carrera: string;
  plan_estudio_id: string;
  ano_ingreso: number;
  registros_trayectoria?: any[];
}

export interface KairosConfig {
  weight_tasa_graduacion: number;
  weight_eficiencia_operativa: number;
  min_tasa_ocupacion: number;
  max_cupos_por_comision: number;
  max_comisiones_a_abrir: number | null;
}

export interface ProcessingRequest {
  plan: Plan;
  estudiantes: Student[];
  config?: KairosConfig;
}

export interface PlanSummary {
  codigo_plan: string;
  nombre_carrera: string;
  facultad: string | null;
  ano_vigencia: number;
  duracion_anos: number;
  total_creditos: number | null;
  cantidad_materias: number;
}

export interface OperationalMetrics {
  comisiones_abiertas: number;
  ingresos_proyectados: number;
  demanda_total: number;
  demanda_satisfecha: number;
  pct_demanda_satisfecha: number;
  aulas_totales: number;
  aulas_usadas: number;
  capacidad_instalada: number;
  pct_ocupacion_aulas: number;
  docentes_totales: number;
  docentes_asignados: number;
  docentes_libres: number;
  pct_docentes_asignados: number;
  cuellos_botella_total: number;
  cuellos_botella_cubiertos: number;
  pct_cuellos_cubiertos: number;
  comisiones_sin_aula: number;
  comisiones_sin_docente: number;
}

export interface ScenarioConfig {
  nombre: string;
  config?: Partial<KairosConfig> | null;
}

export interface ScenarioReport {
  nombre: string;
  config_usada: Record<string, any>;
  metricas: OperationalMetrics;
}

export interface ComparativeReport {
  carrera: string;
  escenarios: ScenarioReport[];
}

export interface PropuestaResumen {
  id: number;
  creada_en: string;
  usuario: string;
  codigo_plan: string;
  carrera: string;
  comisiones_a_abrir: number;
  demanda_total: number;
  materias_con_demanda: number;
  config_usada: Record<string, any>;
}

export interface PropuestaDetalle {
  id: number;
  creada_en: string;
  usuario: string;
  codigo_plan: string;
  publicada: boolean;
  propuesta: any;
}

export const kairosService = {
  async getConfig(): Promise<KairosConfig> {
    const response = await fetch(`${API_BASE_URL}/config`);
    if (!response.ok) {
      throw new Error('Error cargando configuración');
    }
    return response.json();
  },

  async processDemanda(request: ProcessingRequest) {
    const response = await fetch(`${API_BASE_URL}/process`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(request),
    });
    
    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.detail || 'Error procesando la demanda');
    }
    
    return response.json();
  },

  async getGraph(plan: Plan) {
    const response = await fetch(`${API_BASE_URL}/graph`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(plan),
    });

    if (!response.ok) {
      throw new Error('Error cargando el grafo');
    }

    return response.json();
  },

  async listPlanes(): Promise<PlanSummary[]> {
    const response = await fetch(`${API_BASE_URL}/planes`);
    if (!response.ok) {
      throw new Error('Error listando planes');
    }
    return response.json();
  },

  async getPlan(codigoPlan: string): Promise<Plan> {
    const response = await fetch(`${API_BASE_URL}/planes/${encodeURIComponent(codigoPlan)}`);
    if (!response.ok) {
      throw new Error(`Error cargando plan ${codigoPlan}`);
    }
    return response.json();
  },

  async getEstudiantes(codigoPlan: string): Promise<Student[]> {
    const response = await fetch(
      `${API_BASE_URL}/planes/${encodeURIComponent(codigoPlan)}/estudiantes`
    );
    if (!response.ok) {
      throw new Error(`Error cargando estudiantes del plan ${codigoPlan}`);
    }
    return response.json();
  },

  async ingestarPlan(plan: Plan): Promise<PlanSummary> {
    const response = await fetch(`${API_BASE_URL}/planes`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(plan),
    });
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.detail || 'Error ingestando plan');
    }
    return response.json();
  },

  async ingestarEstudiantes(
    estudiantes: Student[]
  ): Promise<{ persistidos: number; rechazados: number; errores: string[] }> {
    const response = await fetch(`${API_BASE_URL}/estudiantes`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(estudiantes),
    });
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.detail || 'Error ingestando estudiantes');
    }
    return response.json();
  },

  async ingestarAulas(
    aulas: any[]
  ): Promise<{ persistidos: number; rechazados: number; errores: string[] }> {
    const response = await fetch(`${API_BASE_URL}/aulas`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(aulas),
    });
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.detail || 'Error ingestando aulas');
    }
    return response.json();
  },

  async ingestarDocentes(
    docentes: any[]
  ): Promise<{ persistidos: number; rechazados: number; errores: string[] }> {
    const response = await fetch(`${API_BASE_URL}/docentes`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(docentes),
    });
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.detail || 'Error ingestando docentes');
    }
    return response.json();
  },

  async processFromDb(codigoPlan: string, config?: KairosConfig) {
    const response = await fetch(
      `${API_BASE_URL}/planes/${encodeURIComponent(codigoPlan)}/process`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...authHeaders() },
        body: JSON.stringify({ config: config ?? null }),
      }
    );

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.detail || 'Error procesando la demanda desde la DB');
    }

    return response.json();
  },

  async listarPropuestas(codigoPlan?: string): Promise<PropuestaResumen[]> {
    const url = codigoPlan
      ? `${API_BASE_URL}/propuestas?codigo_plan=${encodeURIComponent(codigoPlan)}`
      : `${API_BASE_URL}/propuestas`;
    const response = await fetch(url, { headers: authHeaders() });
    if (!response.ok) {
      throw new Error('Error listando propuestas');
    }
    return response.json();
  },

  async getPropuesta(id: number): Promise<PropuestaDetalle> {
    const response = await fetch(`${API_BASE_URL}/propuestas/${id}`, {
      headers: authHeaders(),
    });
    if (!response.ok) {
      throw new Error(`Error cargando propuesta ${id}`);
    }
    return response.json();
  },

  async reporteComparativo(
    codigoPlan: string,
    configuraciones: ScenarioConfig[]
  ): Promise<ComparativeReport> {
    const response = await fetch(
      `${API_BASE_URL}/planes/${encodeURIComponent(codigoPlan)}/reportes/comparativo`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ configuraciones }),
      }
    );

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.detail || 'Error generando el reporte comparativo');
    }

    return response.json();
  },

  async listarPropuestasPublicadas(): Promise<PropuestaResumen[]> {
    const response = await fetch(`${API_BASE_URL}/propuestas/publicadas`, {
      headers: authHeaders(),
    });
    if (!response.ok) {
      throw new Error('Error listando propuestas publicadas');
    }
    return response.json();
  },

  async togglePublicacion(
    id: number,
    publicada: boolean
  ): Promise<{ id: number; publicada: boolean }> {
    const response = await fetch(`${API_BASE_URL}/propuestas/${id}/publicacion`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json', ...authHeaders() },
      body: JSON.stringify({ publicada }),
    });
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.detail || 'Error actualizando publicación');
    }
    return response.json();
  },
};
