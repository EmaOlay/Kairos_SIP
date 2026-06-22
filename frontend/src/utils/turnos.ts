export type Turno = 'manana' | 'tarde' | 'noche';

const TURNO_MAP: Record<string, string> = {
  manana: 'Mañana',
  tarde: 'Tarde',
  noche: 'Noche'
};

export function formatTurno(turno: string): string {
  return TURNO_MAP[turno] || turno;
}

export function formatTurnos(turnos: string[], fallback = '—'): string {
  if (turnos.length === 0) return fallback;
  return turnos.map(formatTurno).join(', ');
}
