import React, { useEffect, useState } from 'react';
import AdminPanel from '../Admin/AdminPanel';
import styles from './SettingsModal.module.css';

interface Props {
  open: boolean;
  onClose: () => void;
}

// Lista de tabs del modal. Pensado para que crecer sea agregar una linea aca
// y un branch en el switch del render.
type SettingsTab = 'admin';

const TABS: { id: SettingsTab; label: string }[] = [
  { id: 'admin', label: 'Administración' },
];

const SettingsModal: React.FC<Props> = ({ open, onClose }) => {
  const [activeTab, setActiveTab] = useState<SettingsTab>('admin');

  // Cerrar con ESC mientras este abierto
  useEffect(() => {
    if (!open) return;
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [open, onClose]);

  if (!open) return null;

  return (
    <div className={styles.overlay} onClick={onClose} role="dialog" aria-modal="true">
      <div className={styles.modal} onClick={(e) => e.stopPropagation()}>
        <header className={styles.modalHeader}>
          <span className={styles.modalTitle}>Configuración</span>
          <button
            type="button"
            className={styles.closeBtn}
            onClick={onClose}
            aria-label="Cerrar"
          >
            ×
          </button>
        </header>

        <div className={styles.tabsBar} role="tablist">
          {TABS.map((t) => (
            <button
              key={t.id}
              role="tab"
              aria-selected={activeTab === t.id}
              className={`${styles.tab} ${activeTab === t.id ? styles.tabActive : ''}`}
              onClick={() => setActiveTab(t.id)}
            >
              {t.label}
            </button>
          ))}
        </div>

        <div className={styles.body}>
          {activeTab === 'admin' && <AdminPanel />}
        </div>
      </div>
    </div>
  );
};

export default SettingsModal;
