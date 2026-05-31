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

export interface ProcessingRequest {
  plan: Plan;
  estudiantes: Student[];
  config?: any;
}

export const kairosService = {
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
  }
};
