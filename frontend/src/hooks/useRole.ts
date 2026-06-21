export type Role = 'Decano' | 'Director' | 'Docente Funcional';

export function useRole(): Role {
  // TODO: reemplazar con rol real cuando se mergee feature/login-roles
  return 'Decano';
}
