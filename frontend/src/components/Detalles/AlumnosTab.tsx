import React, { useState, useCallback, useMemo, useDeferredValue } from 'react';
import type { EstudianteTrayectoria } from '../../services/kairosService';
import { usePaginatedTable } from '../../hooks/usePaginatedTable';
import { formatTurno } from '../../utils/turnos';
import { makeFilterHandler } from './filterUtils';
import styles from './DetallesCommons.module.css';

interface AlumnosTabProps {
  students: EstudianteTrayectoria[];
}

interface AlumnosFilters {
  search: string;
  turno: string;
  anoIngreso: string;
  page: number;
  pageSize: number;
}

const DEFAULT_FILTERS: AlumnosFilters = {
  search: '',
  turno: 'todos',
  anoIngreso: 'todos',
  page: 1,
  pageSize: 25,
};

const AlumnosTab: React.FC<AlumnosTabProps> = ({ students }) => {
  const [filters, setFilters] = useState<AlumnosFilters>(DEFAULT_FILTERS);

  const deferredSearch = useDeferredValue(filters.search);

  const anosIngreso = useMemo(() => {
    return Array.from(new Set(students.map(s => s.ano_ingreso)))
      .filter(a => a != null)
      .sort((a, b) => b - a);
  }, [students]);

  const filterFn = useCallback(
    (s: EstudianteTrayectoria) => {
      const searchLower = deferredSearch.toLowerCase();
      const matchesSearch = searchLower === '' || s.estudiante_id.toLowerCase().includes(searchLower);
      const matchesTurno = filters.turno === 'todos' || s.turno_preferido === filters.turno;
      const matchesAno =
        filters.anoIngreso === 'todos' || String(s.ano_ingreso) === filters.anoIngreso;
      return matchesSearch && matchesTurno && matchesAno;
    },
    [deferredSearch, filters.turno, filters.anoIngreso]
  );

  const paginated = usePaginatedTable({
    items: students,
    filterFn,
    page: filters.page,
    pageSize: filters.pageSize,
  });

  const handleFilterChange = useMemo(() => makeFilterHandler(setFilters), []);

  if (students.length === 0) {
    return (
      <div className={styles.detailsEmpty}>
        <p>No hay alumnos cargados para este plan.</p>
      </div>
    );
  }

  return (
    <>
      <div className={styles.filterBar}>
        <div className={styles.filterRow}>
          <input
            type="text"
            placeholder="Buscar por legajo..."
            value={filters.search}
            onChange={e => handleFilterChange('search', e.target.value)}
            className={styles.filterInput}
            aria-label="Buscar alumno por legajo"
          />
          <select
            value={filters.turno}
            onChange={e => handleFilterChange('turno', e.target.value)}
            className={styles.filterSelect}
            aria-label="Filtrar por turno preferido"
          >
            <option value="todos">Todos los turnos</option>
            <option value="manana">Mañana</option>
            <option value="tarde">Tarde</option>
            <option value="noche">Noche</option>
          </select>
          <select
            value={filters.anoIngreso}
            onChange={e => handleFilterChange('anoIngreso', e.target.value)}
            className={styles.filterSelect}
            aria-label="Filtrar por año de ingreso"
          >
            <option value="todos">Todos los años</option>
            {anosIngreso.map(ano => (
              <option key={ano} value={String(ano)}>
                {ano}
              </option>
            ))}
          </select>
          <button
            onClick={() => setFilters(DEFAULT_FILTERS)}
            className={styles.clearFiltersBtn}
            aria-label="Limpiar filtros de alumnos"
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
                <th>Plan</th>
                <th>Año Ingreso</th>
                <th>Turno Preferido</th>
                <th>Materias Aprobadas</th>
                <th>Promedio</th>
              </tr>
            </thead>
            <tbody>
              {paginated.paginatedItems.map(s => {
                const aprobadas =
                  s.registros_trayectoria?.filter(r => r.estado === 'aprobada') || [];
                const conCalif = aprobadas.filter(r => r.calificacion != null);
                const promedio =
                  conCalif.length > 0
                    ? (
                        conCalif.reduce((acc, r) => acc + (r.calificacion || 0), 0) / conCalif.length
                      ).toFixed(2)
                    : '—';
                return (
                  <tr key={s.estudiante_id}>
                    <td>{s.estudiante_id}</td>
                    <td>{s.plan_estudio_id}</td>
                    <td>{s.ano_ingreso}</td>
                    <td>{formatTurno(s.turno_preferido)}</td>
                    <td>{aprobadas.length}</td>
                    <td>{promedio}</td>
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

export default AlumnosTab;
