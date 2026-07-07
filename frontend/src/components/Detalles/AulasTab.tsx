import React, { useState, useEffect, useCallback, useMemo, useDeferredValue } from 'react';
import { kairosService } from '../../services/kairosService';
import type { Aula } from '../../services/kairosService';
import { usePaginatedTable } from '../../hooks/usePaginatedTable';
import { formatTurnos } from '../../utils/turnos';
import { makeFilterHandler } from './filterUtils';
import styles from './DetallesCommons.module.css';

interface AulasTabProps {
  token: string;
}

interface AulasFilters {
  search: string;
  sede: string;
  turno: string;
  page: number;
  pageSize: number;
}

const DEFAULT_FILTERS: AulasFilters = {
  search: '',
  sede: 'todas',
  turno: 'todos',
  page: 1,
  pageSize: 25,
};

const AulasTab: React.FC<AulasTabProps> = ({ token }) => {
  const [aulas, setAulas] = useState<Aula[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [filters, setFilters] = useState<AulasFilters>(DEFAULT_FILTERS);

  const deferredSearch = useDeferredValue(filters.search);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    (async () => {
      try {
        const aus = await kairosService.getAulas(token);
        if (!cancelled) setAulas(aus);
      } catch (err: any) {
        if (!cancelled) setError(err.message || 'Error cargando aulas');
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [token]);

  const sedes = useMemo(() => {
    const valid = aulas.map(a => a.sede).filter((s): s is string => s != null);
    return Array.from(new Set(valid)).sort((a, b) => a.localeCompare(b, 'es'));
  }, [aulas]);

  const filterFn = useCallback(
    (a: Aula) => {
      const searchLower = deferredSearch.toLowerCase();
      const matchesSearch =
        searchLower === '' ||
        a.aula_id.toLowerCase().includes(searchLower) ||
        a.nombre.toLowerCase().includes(searchLower);
      const matchesSede = filters.sede === 'todas' || a.sede === filters.sede;
      const matchesTurno =
        filters.turno === 'todos' || a.turnos_disponibles.includes(filters.turno);
      return matchesSearch && matchesSede && matchesTurno;
    },
    [deferredSearch, filters.sede, filters.turno]
  );

  const paginated = usePaginatedTable({
    items: aulas,
    filterFn,
    page: filters.page,
    pageSize: filters.pageSize,
  });

  const handleFilterChange = useMemo(() => makeFilterHandler(setFilters), []);

  if (loading) {
    return (
      <div className={styles.detailsEmpty}>
        <p>Cargando aulas...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className={styles.detailsEmpty}>
        <p style={{ color: 'var(--accent-red)' }}>{error}</p>
      </div>
    );
  }

  if (aulas.length === 0) {
    return (
      <div className={styles.detailsEmpty}>
        <p>No hay aulas cargadas en la base de datos.</p>
      </div>
    );
  }

  return (
    <>
      <div className={styles.filterBar}>
        <div className={styles.filterRow}>
          <input
            type="text"
            placeholder="Buscar por aula ID o nombre..."
            value={filters.search}
            onChange={e => handleFilterChange('search', e.target.value)}
            className={styles.filterInput}
            aria-label="Buscar aula por ID o nombre"
          />
          <select
            value={filters.sede}
            onChange={e => handleFilterChange('sede', e.target.value)}
            className={styles.filterSelect}
            aria-label="Filtrar por sede"
          >
            <option value="todas">Todas las sedes</option>
            {sedes.map(sede => (
              <option key={sede} value={sede}>
                {sede}
              </option>
            ))}
          </select>
          <select
            value={filters.turno}
            onChange={e => handleFilterChange('turno', e.target.value)}
            className={styles.filterSelect}
            aria-label="Filtrar por turno disponible"
          >
            <option value="todos">Todos los turnos</option>
            <option value="manana">Mañana</option>
            <option value="tarde">Tarde</option>
            <option value="noche">Noche</option>
          </select>
          <button
            onClick={() => setFilters(DEFAULT_FILTERS)}
            className={styles.clearFiltersBtn}
            aria-label="Limpiar filtros de aulas"
          >
            Limpiar filtros
          </button>
        </div>
        <div className={styles.resultsCount}>
          {paginated.totalFiltered} {paginated.totalFiltered === 1 ? 'resultado' : 'resultados'}
        </div>
      </div>

      {paginated.paginatedItems.length === 0 ? (
        <div className={styles.emptyFiltered}>
          <p>No se encontraron resultados con los filtros aplicados.</p>
        </div>
      ) : (
        <>
          <table className={styles.detailsTable}>
            <thead>
              <tr>
                <th>Aula ID</th>
                <th>Nombre</th>
                <th>Capacidad</th>
                <th>Sede</th>
                <th>Turnos Disponibles</th>
              </tr>
            </thead>
            <tbody>
              {paginated.paginatedItems.map(a => {
                return (
                  <tr key={a.aula_id}>
                    <td>{a.aula_id}</td>
                    <td>{a.nombre}</td>
                    <td>{a.capacidad}</td>
                    <td>{a.sede || '—'}</td>
                    <td>{formatTurnos(a.turnos_disponibles)}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>

          <div className={styles.pagination}>
            <div className={styles.pageSizeSelector}>
              <label>Mostrar:</label>
              <select
                value={filters.pageSize}
                onChange={e => handleFilterChange('pageSize', Number(e.target.value))}
                aria-label="Filas por página"
              >
                <option value="10">10</option>
                <option value="25">25</option>
                <option value="50">50</option>
                <option value="100">100</option>
              </select>
            </div>
            <div className={styles.paginationControls}>
              <button
                onClick={() => handleFilterChange('page', filters.page - 1)}
                disabled={paginated.currentPage === 1}
                className={styles.paginationBtn}
                aria-label="Página anterior"
              >
                ← Anterior
              </button>
              <span className={styles.pageInfo}>
                Página {paginated.currentPage} de {paginated.totalPages}
              </span>
              <button
                onClick={() => handleFilterChange('page', filters.page + 1)}
                disabled={paginated.currentPage >= paginated.totalPages}
                className={styles.paginationBtn}
                aria-label="Página siguiente"
              >
                Siguiente →
              </button>
            </div>
            <div className={styles.resultsInfo}>
              Mostrando {(paginated.currentPage - 1) * filters.pageSize + 1}-
              {Math.min(paginated.currentPage * filters.pageSize, paginated.totalFiltered)} de{' '}
              {paginated.totalFiltered}
            </div>
          </div>
        </>
      )}
    </>
  );
};

export default AulasTab;
