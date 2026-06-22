import React, { useEffect, useState } from 'react';
import { kairosService, type PropuestaResumen } from '../../services/kairosService';
import styles from './HistorialPropuestas.module.css';

interface Props {
  codigoPlan?: string;
  onAbrirPropuesta: (id: number) => void;
  titulo?: string;
  hint?: string;
  fetcher?: (codigoPlan?: string) => Promise<PropuestaResumen[]>;
}

const formatFecha = (iso: string): string => {
  try {
    return new Date(iso).toLocaleString('es-AR', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
    });
  } catch {
    return iso;
  }
};

const formatConfig = (config: Record<string, any>): string => {
  const cascada = config.weight_tasa_graduacion;
  const rent = config.weight_eficiencia_operativa;
  const scoreMin = config.min_tasa_ocupacion;
  const tope = config.max_comisiones_a_abrir;
  return (
    `Cascada ${Math.round((cascada ?? 0) * 100)}% · ` +
    `Rentabilidad ${Math.round((rent ?? 0) * 100)}% · ` +
    `Score mín ${((scoreMin ?? 0) * 10).toFixed(1)} · ` +
    `Tope ${tope ?? 'sin límite'}`
  );
};

const HistorialPropuestas: React.FC<Props> = ({
  codigoPlan,
  onAbrirPropuesta,
  titulo = 'Historial de propuestas',
  hint = 'Cada vez que prendés el motor, la propuesta queda registrada con su config.',
  fetcher = kairosService.listarPropuestas,
}) => {
  const [propuestas, setPropuestas] = useState<PropuestaResumen[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const cargar = async () => {
    setLoading(true);
    setError(null);
    try {
      const lista = await fetcher(codigoPlan);
      setPropuestas(lista);
    } catch (err: any) {
      setError(err.message || 'Error cargando historial');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    cargar();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [codigoPlan]);

  return (
    <div className={styles.wrapper}>
      <div className={styles.toolbar}>
        <div>
          <h3 className={styles.title}>{titulo}</h3>
          <span className={styles.hint}>{hint}</span>
        </div>
        <button className={styles.refreshBtn} onClick={cargar} disabled={loading}>
          {loading ? 'Cargando…' : '↻ Refrescar'}
        </button>
      </div>

      {error && <div className={styles.error}>{error}</div>}

      {!loading && propuestas.length === 0 && !error ? (
        <div className={styles.empty}>
          Todavía no hay propuestas guardadas para este plan. Dale a “Prender Motor”.
        </div>
      ) : (
        <div className={styles.tableWrap}>
          <table className={styles.table}>
            <thead>
              <tr>
                <th>#</th>
                <th>Fecha</th>
                <th>Usuario</th>
                <th>Comisiones a abrir</th>
                <th>Demanda total</th>
                <th>Configuración</th>
              </tr>
            </thead>
            <tbody>
              {propuestas.map((p) => (
                <tr key={p.id}>
                  <td>{p.id}</td>
                  <td>
                    <button
                      type="button"
                      className={styles.fechaLink}
                      onClick={() => onAbrirPropuesta(p.id)}
                      title="Ver esta propuesta"
                    >
                      {formatFecha(p.creada_en)}
                    </button>
                  </td>
                  <td>
                    <span className={styles.usuarioBadge}>{p.usuario}</span>
                  </td>
                  <td>{p.comisiones_a_abrir}</td>
                  <td>{p.demanda_total}</td>
                  <td className={styles.configCell}>{formatConfig(p.config_usada)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};

export default HistorialPropuestas;
