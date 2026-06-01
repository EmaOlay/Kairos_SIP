const API_BASE_URL = 'http://localhost:8000/api/v1';

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

  async processFromDb(codigoPlan: string, config?: KairosConfig) {
    const response = await fetch(
      `${API_BASE_URL}/planes/${encodeURIComponent(codigoPlan)}/process`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ config: config ?? null }),
      }
    );

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.detail || 'Error procesando la demanda desde la DB');
    }

    return response.json();
  },
};
