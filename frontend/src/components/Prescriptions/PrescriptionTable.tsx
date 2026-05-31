import React from 'react';
import styles from './PrescriptionTable.module.css';

interface Prescription {
  codigo: string;
  nombre: string;
  decision: 'ABRIR' | 'NO ABRIR';
  razon: string;
  demanda: number;
}

interface PrescriptionTableProps {
  prescriptions: Record<string, Prescription>;
}

const PrescriptionTable: React.FC<PrescriptionTableProps> = ({ prescriptions }) => {
  const items = Object.values(prescriptions).sort((a, b) => b.demanda - a.demanda);

  return (
    <div className={styles.container}>
      <h3 className={styles.title}>Prescripciones de Apertura</h3>
      <div className={styles.tableWrapper}>
        <table className={styles.table}>
          <thead>
            <tr>
              <th>Código</th>
              <th>Materia</th>
              <th>Demanda</th>
              <th>Decisión</th>
              <th>Razón</th>
            </tr>
          </thead>
          <tbody>
            {items.map((item) => (
              <tr key={item.codigo}>
                <td className={styles.code}>{item.codigo}</td>
                <td className={styles.name}>{item.nombre}</td>
                <td className={styles.demand}>{item.demanda}</td>
                <td>
                  <span className={`${styles.badge} ${item.decision === 'ABRIR' ? styles.abrir : styles.noAbrir}`}>
                    {item.decision}
                  </span>
                </td>
                <td className={styles.reason}>{item.razon}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default PrescriptionTable;
