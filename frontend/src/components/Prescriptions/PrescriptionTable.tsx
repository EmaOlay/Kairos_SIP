import React from 'react';
import styles from './PrescriptionTable.module.css';

interface Prescription {
  codigo: string;
  nombre: string;
  turno: string;
  ingreso_por_alumno: number;
  decision: 'ABRIR' | 'NO ABRIR';
  razon: string;
  demanda: number;
  score: number;
  desbloquea: number;
  aula?: string;
  docente?: string;
  bajo_cupo?: boolean;
}

interface PrescriptionTableProps {
  prescriptions: Record<string, Prescription>;
  weightCascada: number;
  weightRentabilidad: number;
}

const turnoLabel: Record<string, string> = {
  manana: 'Mañana',
  tarde: 'Tarde',
  noche: 'Noche',
};

const PrescriptionTable: React.FC<PrescriptionTableProps> = ({ prescriptions, weightCascada, weightRentabilidad }) => {
  const items = Object.values(prescriptions).sort((a, b) => b.score - a.score);

  const buildScoreTooltip = (item: Prescription) => {
    const rentabilidad = (item.demanda * item.ingreso_por_alumno / 30000);
    return [
      `Score = (${weightCascada.toFixed(1)} × ${item.desbloquea}) + (${weightRentabilidad.toFixed(1)} × ${rentabilidad.toFixed(1)})`,
      ``,
      `Cascada: ${item.desbloquea} materias se desbloquean en cadena`,
      `Rentabilidad: ${item.demanda} alumnos × $${item.ingreso_por_alumno} / 30000 = ${rentabilidad.toFixed(1)}`,
      ``,
      `Peso cascada: ${(weightCascada * 100).toFixed(0)}% | Peso rentabilidad: ${(weightRentabilidad * 100).toFixed(0)}%`,
    ].join('\n');
  };

  return (
    <div className={styles.container}>
      <h3 className={styles.title}>Prescripciones de Apertura</h3>
      <div className={styles.tableWrapper}>
        <table className={styles.table}>
          <thead>
            <tr>
              <th title="Posición en el ranking ordenado por score">#</th>
              <th title="Nombre de la asignatura del plan de estudio">Materia</th>
              <th title="Turno de la comisión: Mañana ($3000), Tarde ($4000), Noche ($6000)">Turno</th>
              <th title="Aula asignada para el dictado">Aula</th>
              <th title="Docente requerido o asignado">Profesor</th>
              <th title="Lo que la facultad cobra por alumno inscripto en este turno">Ingreso/alumno</th>
              <th title="Puntaje calculado por el motor. Pasá el mouse sobre cada celda de score para ver la fórmula detallada">Score</th>
              <th title="Cantidad de alumnos que necesitan esta materia y prefieren este turno">Demanda</th>
              <th title="Cuántas materias se habilitan transitivamente en la carrera si se aprueba esta">Desbloquea</th>
              <th title="ABRIR = el motor recomienda abrir. NO ABRIR = no conviene con estos parámetros">Decisión</th>
              <th title="Justificación generada por el motor según score, presupuesto y cascada">Razón</th>
            </tr>
          </thead>
          <tbody>
            {items.map((item, idx) => {
              const showRisk = item.bajo_cupo && item.decision === 'ABRIR';
              return (
                <tr key={`${item.codigo}_${item.turno}`} className={showRisk ? styles.riskRow : ''}>
                  <td className={styles.rank}>{idx + 1}</td>
                  <td className={styles.name}>{item.nombre}</td>
                  <td className={styles.turno}>{turnoLabel[item.turno] || item.turno}</td>
                  <td className={styles.turno}>{item.aula || '-'}</td>
                  <td className={styles.name}>{item.docente || '-'}</td>
                  <td className={styles.costo}>${item.ingreso_por_alumno?.toLocaleString()}</td>
                  <td className={styles.score} title={buildScoreTooltip(item)}>{item.score?.toFixed(1)}</td>
                  <td className={styles.demand}>
                    <div className={styles.bajoCupoRow}>
                      {item.demanda}
                      {showRisk && (
                        <span className={styles.bajoCupoBadge} title="Bajo cupo proyectado. Menos de 15 alumnos.">
                          ⚠️ Riesgo
                        </span>
                      )}
                    </div>
                  </td>
                  <td className={styles.demand}>{item.desbloquea}</td>
                  <td>
                    <span className={`${styles.badge} ${item.decision === 'ABRIR' ? styles.abrir : styles.noAbrir}`}>
                      {item.decision}
                    </span>
                  </td>
                  <td className={styles.reason}>{item.razon}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default PrescriptionTable;
