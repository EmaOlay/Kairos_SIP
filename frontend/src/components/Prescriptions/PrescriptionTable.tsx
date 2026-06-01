import React from 'react';
import styles from './PrescriptionTable.module.css';

interface Prescription {
  codigo: string;
  nombre: string;
  turno: string;
  costo: number;
  decision: 'ABRIR' | 'NO ABRIR';
  demanda: number;
  score: number;
  desbloquea: number;
}

interface PrescriptionTableProps {
  prescriptions: Record<string, Prescription>;
}

const turnoLabel: Record<string, string> = {
  manana: 'Mañana',
  tarde: 'Tarde',
  noche: 'Noche',
};

const PrescriptionTable: React.FC<PrescriptionTableProps> = ({ prescriptions }) => {
  const items = Object.values(prescriptions).sort((a, b) => b.score - a.score);

  return (
    <div className={styles.container}>
      <h3 className={styles.title}>Prescripciones de Apertura</h3>
      <div className={styles.tableWrapper}>
        <table className={styles.table}>
          <thead>
            <tr>
              <th>#</th>
              <th>Materia</th>
              <th>Turno</th>
              <th>Costo</th>
              <th>Score</th>
              <th>Demanda</th>
              <th>Desbloquea</th>
              <th>Decisión</th>
            </tr>
          </thead>
          <tbody>
            {items.map((item, idx) => (
              <tr key={`${item.codigo}_${item.turno}`}>
                <td className={styles.rank}>{idx + 1}</td>
                <td className={styles.name}>{item.nombre}</td>
                <td className={styles.turno}>{turnoLabel[item.turno] || item.turno}</td>
                <td className={styles.costo}>${item.costo?.toLocaleString()}</td>
                <td className={styles.score}>{item.score?.toFixed(1)}</td>
                <td className={styles.demand}>{item.demanda}</td>
                <td className={styles.demand}>{item.desbloquea}</td>
                <td>
                  <span className={`${styles.badge} ${item.decision === 'ABRIR' ? styles.abrir : styles.noAbrir}`}>
                    {item.decision}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default PrescriptionTable;
