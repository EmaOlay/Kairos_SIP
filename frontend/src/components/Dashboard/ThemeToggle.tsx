import React, { useEffect, useState } from 'react';
import styles from './ThemeToggle.module.css';

type Theme = 'dark' | 'light';

const STORAGE_KEY = 'kairos-theme';

function getInitialTheme(): Theme {
  const stored = localStorage.getItem(STORAGE_KEY);
  if (stored === 'light' || stored === 'dark') return stored;
  // Respetar la preferencia del sistema en la primera visita.
  if (window.matchMedia?.('(prefers-color-scheme: light)').matches) return 'light';
  return 'dark';
}

/**
 * Aplica el tema seteando data-theme en <html> (las variables CSS se encargan
 * del resto) y lo persiste en localStorage. Dark es el default.
 */
const ThemeToggle: React.FC = () => {
  const [theme, setTheme] = useState<Theme>(getInitialTheme);

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem(STORAGE_KEY, theme);
  }, [theme]);

  const toggle = () => setTheme((t) => (t === 'dark' ? 'light' : 'dark'));

  return (
    <button
      className={styles.toggle}
      onClick={toggle}
      title={theme === 'dark' ? 'Cambiar a tema claro' : 'Cambiar a tema oscuro'}
      aria-label="Cambiar tema"
    >
      <span className={styles.icon}>{theme === 'dark' ? '☀️' : '🌙'}</span>
      <span className={styles.label}>{theme === 'dark' ? 'Claro' : 'Oscuro'}</span>
    </button>
  );
};

export default ThemeToggle;
