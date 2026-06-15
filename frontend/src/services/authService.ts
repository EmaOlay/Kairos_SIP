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
};
