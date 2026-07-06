import React, { useState, useEffect, useCallback, useMemo, useDeferredValue } from 'react';
import { kairosService } from '../../services/kairosService';
import type { Docente } from '../../services/kairosService';
import { usePaginatedTable } from '../../hooks/usePaginatedTable';
import { formatTurnos } from '../../utils/turnos';
import { makeFilterHandler } from './filterUtils';
import styles from './DetallesCommons.module.css';

interface DocentesTabProps {
  token: string;
}

interface DocentesFilters {
  search: string;
  turno: string;
  horarioFehaciente: string;
  page: number;
  pageSize: number;
}

const DEFAULT_FILTERS: DocentesFilters = {
  search: '',
  turno: 'todos',
  horarioFehaciente: 'todos',
  page: 1,
  pageSize: 25,
};

const DocentesTab: React.FC<DocentesTabProps> = ({ token }) => {
  const [docentes, setDocentes] = useState<Docente[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [filters, setFilters] = useState<DocentesFilters>(DEFAULT_FILTERS);

  const deferredSearch = useDeferredValue(filters.search);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    (async () => {
      try {
        const docs = await kairosService.getDocentes(token);
        if (!cancelled) setDocentes(docs);
      } catch (err: any) {
        if (!cancelled) setError(err.message || 'Error cargando docentes');
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [token]);

  const filterFn = useCallback(
    (d: Docente) => {
      const searchLower = deferredSearch.toLowerCase();
      const matchesSearch =
        searchLower === '' ||
        d.docente_id.toLowerCase().includes(searchLower) ||
        d.nombre.toLowerCase().includes(searchLower);
      const matchesTurno =
        filters.turno === 'todos' || d.disponibilidad_turnos.includes(filters.turno);
      const matchesHorario =
        filters.horarioFehaciente === 'todos' ||
        (filters.horarioFehaciente === 'si' ? d.horario_fehaciente : !d.horario_fehaciente);
      return matchesSearch && matchesTurno && matchesHorario;
    },
    [deferredSearch, filters.turno, filters.horarioFehaciente]
  );

  const paginated = usePaginatedTable({
    items: docentes,
    filterFn,
    page: filters.page,
    pageSize: filters.pageSize,
  });

  const handleFilterChange = useMemo(() => makeFilterHandler(setFilters), []);

  if (loading) {
    return (
      <div className={styles.detailsEmpty}>
        <p>Cargando docentes...</p>
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

  if (docentes.length === 0) {
    return (
      <div className={styles.detailsEmpty}>
        <p>No hay docentes cargados en la base de datos.</p>
      </div>
    );
  }

  return (
    <>
      <div className={styles.filterBar}>
        <div className={styles.filterRow}>
          <input
            type="text"
            placeholder="Buscar por legajo o nombre..."
            value={filters.search}
            onChange={e => handleFilterChange('search', e.target.value)}
            className={styles.filterInput}
            aria-label="Buscar docente por legajo o nombre"
          />
          <select
            value={filters.turno}
            onChange={e => handleFilterChange('turno', e.target.value)}
            className={styles.filterSelect}
            aria-label="Filtrar por turno"
          >
            <option value="todos">Todos los turnos</option>
            <option value="manana">Mañana</option>
            <option value="tarde">Tarde</option>
            <option value="noche">Noche</option>
          </select>
          <select
            value={filters.horarioFehaciente}
            onChange={e => handleFilterChange('horarioFehaciente', e.target.value)}
            className={styles.filterSelect}
            aria-label="Filtrar por horario fehaciente"
          >
            <option value="todos">Horario fehaciente: todos</option>
            <option value="si">Horario fehaciente: sí</option>
            <option value="no">Horario fehaciente: no</option>
          </select>
          <button
            onClick={() => setFilters(DEFAULT_FILTERS)}
            className={styles.clearFiltersBtn}
            aria-label="Limpiar filtros de docentes"
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
                <th>Legajo</th>
                <th>Nombre</th>
                <th>Materias que Dicta</th>
                <th>Disponibilidad</th>
                <th>Max Comisiones</th>
                <th>Horario Fehaciente</th>
              </tr>
            </thead>
            <tbody>
              {paginated.paginatedItems.map(d => {
                const materiasDisplay =
                  d.materias_que_dicta.length > 0 ? d.materias_que_dicta.join(', ') : '—';
                return (
                  <tr key={d.docente_id}>
                    <td>{d.docente_id}</td>
                    <td>{d.nombre}</td>
                    <td>{materiasDisplay}</td>
                    <td>{formatTurnos(d.disponibilidad_turnos)}</td>
                    <td>{d.max_comisiones}</td>
                    <td>
                      {d.horario_fehaciente ? 'Sí' : 'No'}
                    </td>
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

export default DocentesTab;
