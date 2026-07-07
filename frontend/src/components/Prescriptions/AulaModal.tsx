import React, { useEffect, useRef } from 'react';
import styles from './AulaModal.module.css';

interface AulaModalProps {
  open: boolean;
  onClose: () => void;
  aulaId: string;
  aulaNombre: string;
  capacidad: number;
  demanda: number;
}

const SEATS_PER_ROW = 10;

const Seat = ({ numero, ocupado }: { numero: number; ocupado: boolean }) => (
  <div
    className={`${styles.seat} ${ocupado ? styles.seatOccupied : styles.seatFree}`}
    aria-label={`Butaca ${numero}, ${ocupado ? 'ocupada' : 'libre'}`}
    role="img"
  >
    {numero}
  </div>
);

const AulaModal: React.FC<AulaModalProps> = ({ open, onClose, aulaId, aulaNombre, capacidad, demanda }) => {
  const closeBtnRef = useRef<HTMLButtonElement>(null);
  const previousActiveElement = useRef<HTMLElement | null>(null);

  useEffect(() => {
    if (!open) return;

    previousActiveElement.current = document.activeElement as HTMLElement;
    document.body.style.overflow = 'hidden';

    setTimeout(() => closeBtnRef.current?.focus(), 100);

    const handleEsc = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', handleEsc);

    return () => {
      window.removeEventListener('keydown', handleEsc);
      document.body.style.overflow = '';
      previousActiveElement.current?.focus();
    };
  }, [open, onClose]);

  if (!open) return null;

  const renderContent = () => {
    if (capacidad === 0) {
      return <div className={styles.message}>Esta aula no tiene capacidad configurada.</div>;
    }

    const fullRows = Math.floor(capacidad / SEATS_PER_ROW);
    const remainder = capacidad % SEATS_PER_ROW;
    const ocupados = Math.min(demanda, capacidad);
    const sobrecupo = demanda > capacidad ? demanda - capacidad : 0;

    const rows: Array<{ left: number[]; right: number[] }> = [];
    let seatNumber = 1;

    for (let i = 0; i < fullRows; i++) {
      const left = Array.from({ length: 5 }, (_, idx) => seatNumber + idx);
      seatNumber += 5;
      const right = Array.from({ length: 5 }, (_, idx) => seatNumber + idx);
      seatNumber += 5;
      rows.push({ left, right });
    }

    if (remainder > 0) {
      const leftCount = remainder === 1 ? 1 : Math.floor(remainder / 2);
      const rightCount = remainder - leftCount;
      const left = Array.from({ length: leftCount }, (_, idx) => seatNumber + idx);
      seatNumber += leftCount;
      const right = Array.from({ length: rightCount }, (_, idx) => seatNumber + idx);
      rows.push({ left, right });
    }

    return (
      <>
        <div className={styles.frente}>Frente</div>
        <div className={styles.aulaGrid}>
          {rows.map((row, idx) => (
            <div key={idx} className={styles.aulaRow}>
              <div className={styles.aulaSide}>
                {row.left.map(num => (
                  <Seat key={num} numero={num} ocupado={num <= ocupados} />
                ))}
              </div>
              <div className={styles.aulaSide}>
                {row.right.map(num => (
                  <Seat key={num} numero={num} ocupado={num <= ocupados} />
                ))}
              </div>
            </div>
          ))}
        </div>
        {sobrecupo > 0 && (
          <div className={styles.overflowBadge}>
            Sobrecupo: +{sobrecupo} alumnos sin asiento
          </div>
        )}
        <div className={styles.legend}>
          <div className={styles.legendItem}>
            <div className={`${styles.legendBox} ${styles.legendBoxOccupied}`}></div>
            <span>Ocupado</span>
          </div>
          <div className={styles.legendItem}>
            <div className={`${styles.legendBox} ${styles.legendBoxFree}`}></div>
            <span>Libre</span>
          </div>
        </div>
      </>
    );
  };

  return (
    <div className={styles.overlay} onClick={onClose}>
      <div
        className={styles.modal}
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
        aria-labelledby="aula-modal-title"
      >
        <header className={styles.modalHeader}>
          <div>
            <h2 id="aula-modal-title" className={styles.modalTitle}>
              Aula {aulaNombre}
            </h2>
            <p className={styles.modalSubtitle}>
              ID: {aulaId} | Capacidad: {capacidad} | Asignados: {demanda}
            </p>
          </div>
          <button
            ref={closeBtnRef}
            type="button"
            className={styles.closeBtn}
            onClick={onClose}
            aria-label="Cerrar"
          >
            ×
          </button>
        </header>

        <div className={styles.body}>
          {renderContent()}
        </div>
      </div>
    </div>
  );
};

export default AulaModal;
