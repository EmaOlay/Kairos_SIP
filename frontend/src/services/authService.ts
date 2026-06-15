const API_BASE_URL = 'http://localhost:8000/api/v1';
const TOKEN_STORAGE_KEY = 'kairos_auth_token';

export type Rol = 'docente_funcional' | 'director_departamento' | 'decano';

export interface User {
  id: number | string;
  username: string;
  nombre: string;
  rol: Rol;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  user: User;
}

export interface CreateUserPayload {
  username: string;
  password: string;
  nombre: string;
  rol: Rol;
}

export function getStoredToken(): string | null {
  return localStorage.getItem(TOKEN_STORAGE_KEY);
}

export function setStoredToken(token: string): void {
  localStorage.setItem(TOKEN_STORAGE_KEY, token);
}

export function clearStoredToken(): void {
  localStorage.removeItem(TOKEN_STORAGE_KEY);
}

export function rolLabel(rol: Rol): string {
  switch (rol) {
    case 'docente_funcional':
      return 'Docente Funcional';
    case 'director_departamento':
      return 'Director de Departamento';
    case 'decano':
      return 'Decano';
    default:
      return rol;
  }
}

export const authService = {
  async login(username: string, password: string): Promise<LoginResponse> {
    const response = await fetch(`${API_BASE_URL}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password }),
    });

    if (response.status === 401) {
      throw new Error('Usuario o contraseña incorrectos');
    }

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.detail || 'Error al iniciar sesión');
    }

    return response.json();
  },

  async me(token: string): Promise<User> {
    const response = await fetch(`${API_BASE_URL}/auth/me`, {
      headers: { Authorization: `Bearer ${token}` },
    });

    if (!response.ok) {
      throw new Error('Token inválido o expirado');
    }

    return response.json();
  },

  async listUsers(token: string): Promise<User[]> {
    const response = await fetch(`${API_BASE_URL}/users`, {
      headers: { Authorization: `Bearer ${token}` },
    });

    if (response.status === 401) {
      throw new Error('Sesión expirada, volvé a iniciar sesión');
    }
    if (response.status === 403) {
      throw new Error('No tenés permisos para ver esta sección');
    }
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(detailToMessage(errorData) || 'Error listando usuarios');
    }

    return response.json();
  },

  async createUser(token: string, payload: CreateUserPayload): Promise<User> {
    const response = await fetch(`${API_BASE_URL}/users`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify(payload),
    });

    if (response.status === 401) {
      throw new Error('Sesión expirada, volvé a iniciar sesión');
    }
    if (response.status === 403) {
      throw new Error('No tenés permisos para crear usuarios');
    }
    if (response.status === 409) {
      throw new Error('Ya existe un usuario con ese username');
    }
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(detailToMessage(errorData) || 'Error creando usuario');
    }

    return response.json();
  },
};

// Pydantic devuelve `detail` como array de objetos en errores 422.
// Acá lo serializamos a algo legible para el usuario.
function detailToMessage(errorData: unknown): string | null {
  if (!errorData || typeof errorData !== 'object') return null;
  const detail = (errorData as { detail?: unknown }).detail;
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail)) {
    return detail
      .map((d) => (typeof d === 'object' && d && 'msg' in d ? String((d as { msg: unknown }).msg) : String(d)))
      .join('; ');
  }
  return null;
}
