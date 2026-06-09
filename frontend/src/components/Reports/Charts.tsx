import React from 'react';
import styles from './Charts.module.css';

/**
 * Gráficos en SVG puro, sin dependencias externas. Todos los colores salen
 * de variables CSS (var(--chart-*), var(--text-*)) así respetan light/dark
 * theme automáticamente.
 */

export interface Series {
  /** Etiqueta de la serie (nombre del escenario). */
  label: string;
  /** Color CSS (ej. 'var(--chart-1)'). */
  color: string;
  /** Un valor por categoría, en el mismo orden que `categories`. */
  values: number[];
}

interface GroupedBarChartProps {
  categories: string[];
  series: Series[];
  /** Formatea el valor para el tooltip/etiqueta. */
  format?: (v: number) => string;
  height?: number;
  /** Sufijo del eje Y (ej. '%'). */
  unit?: string;
}

/**
 * Barras agrupadas: una categoría por grupo, una barra por escenario.
 * Ideal para comparar 2-3 configs sobre varias métricas a la vez.
 */
export const GroupedBarChart: React.FC<GroupedBarChartProps> = ({
  categories,
  series,
  format = (v) => String(v),
  height = 280,
  unit = '',
}) => {
  const width = 720;
  const padding = { top: 20, right: 16, bottom: 48, left: 48 };
  const plotW = width - padding.left - padding.right;
  const plotH = height - padding.top - padding.bottom;

  const allValues = series.flatMap((s) => s.values);
  const rawMax = Math.max(1, ...allValues);
  // "Lindo" tope de eje: redondea hacia arriba.
  const maxVal = niceCeil(rawMax);

  const groupW = plotW / categories.length;
  const barGap = 6;
  const innerW = groupW * 0.7;
  const barW = (innerW - barGap * (series.length - 1)) / series.length;

  const ticks = 4;
  const yTicks = Array.from({ length: ticks + 1 }, (_, i) => (maxVal / ticks) * i);

  return (
    <div className={styles.chartBox}>
      <svg
        viewBox={`0 0 ${width} ${height}`}
        className={styles.svg}
        role="img"
        preserveAspectRatio="xMidYMid meet"
      >
        {/* Grid + eje Y */}
        {yTicks.map((t, i) => {
          const y = padding.top + plotH - (t / maxVal) * plotH;
          return (
            <g key={i}>
              <line
                x1={padding.left}
                y1={y}
                x2={width - padding.right}
                y2={y}
                stroke="var(--chart-grid)"
                strokeWidth={1}
              />
              <text x={padding.left - 8} y={y + 4} className={styles.axisLabel} textAnchor="end">
                {shortNum(t)}
                {unit}
              </text>
            </g>
          );
        })}

        {/* Barras */}
        {categories.map((cat, ci) => {
          const groupX = padding.left + groupW * ci + (groupW - innerW) / 2;
          return (
            <g key={cat}>
              {series.map((s, si) => {
                const v = s.values[ci] ?? 0;
                const h = (v / maxVal) * plotH;
                const x = groupX + si * (barW + barGap);
                const y = padding.top + plotH - h;
                return (
                  <g key={s.label}>
                    <rect
                      x={x}
                      y={y}
                      width={barW}
                      height={Math.max(0, h)}
                      rx={3}
                      fill={s.color}
                      className={styles.bar}
                    >
                      <title>{`${s.label} — ${cat}: ${format(v)}`}</title>
                    </rect>
                    {h > 18 && (
                      <text x={x + barW / 2} y={y - 5} className={styles.barValue} textAnchor="middle">
                        {shortNum(v)}
                      </text>
                    )}
                  </g>
                );
              })}
              <text
                x={padding.left + groupW * ci + groupW / 2}
                y={height - padding.bottom + 18}
                className={styles.catLabel}
                textAnchor="middle"
              >
                {cat}
              </text>
            </g>
          );
        })}

        {/* Eje X base */}
        <line
          x1={padding.left}
          y1={padding.top + plotH}
          x2={width - padding.right}
          y2={padding.top + plotH}
          stroke="var(--chart-grid)"
          strokeWidth={1.5}
        />
      </svg>
    </div>
  );
};

interface GaugeProps {
  /** 0-100 */
  percent: number;
  label: string;
  color?: string;
  size?: number;
}

/** Medidor circular (donut) para porcentajes. */
export const Gauge: React.FC<GaugeProps> = ({ percent, label, color = 'var(--chart-1)', size = 130 }) => {
  const stroke = 12;
  const r = (size - stroke) / 2;
  const c = 2 * Math.PI * r;
  const clamped = Math.max(0, Math.min(100, percent));
  const dash = (clamped / 100) * c;

  return (
    <div className={styles.gauge}>
      <svg viewBox={`0 0 ${size} ${size}`} width={size} height={size}>
        <circle
          cx={size / 2}
          cy={size / 2}
          r={r}
          fill="none"
          stroke="var(--chart-grid)"
          strokeWidth={stroke}
        />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={r}
          fill="none"
          stroke={color}
          strokeWidth={stroke}
          strokeLinecap="round"
          strokeDasharray={`${dash} ${c - dash}`}
          transform={`rotate(-90 ${size / 2} ${size / 2})`}
          className={styles.gaugeArc}
        />
        <text x="50%" y="48%" className={styles.gaugeValue} textAnchor="middle">
          {clamped.toFixed(0)}%
        </text>
      </svg>
      <span className={styles.gaugeLabel}>{label}</span>
    </div>
  );
};

interface LegendProps {
  series: { label: string; color: string }[];
}

export const Legend: React.FC<LegendProps> = ({ series }) => (
  <div className={styles.legend}>
    {series.map((s) => (
      <span key={s.label} className={styles.legendItem}>
        <span className={styles.legendSwatch} style={{ background: s.color }} />
        {s.label}
      </span>
    ))}
  </div>
);

// --- helpers ---
function niceCeil(v: number): number {
  if (v <= 0) return 1;
  const mag = Math.pow(10, Math.floor(Math.log10(v)));
  const norm = v / mag;
  const step = norm <= 1 ? 1 : norm <= 2 ? 2 : norm <= 5 ? 5 : 10;
  return step * mag;
}

function shortNum(v: number): string {
  if (Math.abs(v) >= 1_000_000) return `${(v / 1_000_000).toFixed(1)}M`;
  if (Math.abs(v) >= 1_000) return `${(v / 1_000).toFixed(v >= 10_000 ? 0 : 1)}k`;
  return Number.isInteger(v) ? String(v) : v.toFixed(1);
}
