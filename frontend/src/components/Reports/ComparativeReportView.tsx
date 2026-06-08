import React, { useMemo, useState } from 'react';
import {
  kairosService,
  type KairosConfig,
  type ComparativeReport,
  type ScenarioConfig,
} from '../../services/kairosService';
import { GroupedBarChart, Gauge, Legend, type Series } from './Charts';
import styles from './ComparativeReportView.module.css';

interface Props {
  codigoPlan: string;
  baseConfig: KairosConfig;
}

const SCENARIO_COLORS = ['var(--chart-1)', 'var(--chart-2)', 'var(--chart-3)'];

/**
 * Define los 3 escenarios por defecto a partir de la config activa del panel.
 * Son variaciones representativas para que la comparativa muestre algo útil de
 * entrada: el usuario puede ajustarlas con los controles.
 */
function buildDefaultScenarios(base: KairosConfig): ScenarioConfig[] {
  return [
    {
      nombre: 'Pro-graduación',
      config: { ...base, weight_tasa_graduacion: 0.8, weight_eficiencia_operativa: 0.2 },
    },
    {
      nombre: 'Balanceado',
      config: { ...base, weight_tasa_graduacion: 0.5, weight_eficiencia_operativa: 0.5 },
    },
    {
      nombre: 'Pro-rentabilidad',
      config: { ...base, weight_tasa_graduacion: 0.2, weight_eficiencia_operativa: 0.8 },
    },
  ];
}

const fmtMoney = (v: number) => `$${v.toLocaleString('es-AR')}`;
const fmtInt = (v: number) => v.toLocaleString('es-AR');

const ComparativeReportView: React.FC<Props> = ({ codigoPlan, baseConfig }) => {
  const [scenarios, setScenarios] = useState<ScenarioConfig[]>(() => buildDefaultScenarios(baseConfig));
  const [report, setReport] = useState<ComparativeReport | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [count, setCount] = useState<2 | 3>(3);

  const activeScenarios = scenarios.slice(0, count);

  const run = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await kairosService.reporteComparativo(codigoPlan, activeScenarios);
      setReport(res);
    } catch (err: any) {
      setError(err.message || 'Error generando el reporte');
    } finally {
      setLoading(false);
    }
  };

  const legend = useMemo(
    () =>
      (report?.escenarios ?? []).map((e, i) => ({
        label: e.nombre,
        color: SCENARIO_COLORS[i % SCENARIO_COLORS.length],
      })),
    [report]
  );

  // Series por métrica para el gráfico de barras agrupadas.
  const charts = useMemo(() => {
    if (!report) return null;
    const esc = report.escenarios;
    const colorOf = (i: number) => SCENARIO_COLORS[i % SCENARIO_COLORS.length];

    const ingresos: Series[] = esc.map((e, i) => ({
      label: e.nombre,
      color: colorOf(i),
      values: [e.metricas.ingresos_proyectados],
    }));

    // Porcentajes agrupados en un solo gráfico comparable (todos 0-100).
    const porcentajes: Series[] = esc.map((e, i) => ({
      label: e.nombre,
      color: colorOf(i),
      values: [
        e.metricas.pct_demanda_satisfecha,
        e.metricas.pct_ocupacion_aulas,
        e.metricas.pct_docentes_asignados,
        e.metricas.pct_cuellos_cubiertos,
      ],
    }));

    return { ingresos, porcentajes };
  }, [report]);

  return (
    <div className={styles.wrapper}>
      <div className={styles.toolbar}>
        <div className={styles.scenarioToggle}>
          <span className={styles.toolbarLabel}>Escenarios a comparar:</span>
          <button
            className={`${styles.countBtn} ${count === 2 ? styles.countActive : ''}`}
            onClick={() => setCount(2)}
          >
            2
          </button>
          <button
            className={`${styles.countBtn} ${count === 3 ? styles.countActive : ''}`}
            onClick={() => setCount(3)}
          >
            3
          </button>
        </div>
        <button className={styles.runBtn} onClick={run} disabled={loading}>
          {loading ? 'Generando…' : '📊 Generar comparativa'}
        </button>
      </div>

      {/* Editor de escenarios: nombre + peso cascada/rentabilidad */}
      <div className={styles.scenarioEditor}>
        {activeScenarios.map((sc, idx) => {
          const grad = sc.config?.weight_tasa_graduacion ?? 0.5;
          return (
            <div key={idx} className={styles.scenarioCard}>
              <span
                className={styles.scenarioDot}
                style={{ background: SCENARIO_COLORS[idx % SCENARIO_COLORS.length] }}
              />
              <input
                className={styles.scenarioName}
                value={sc.nombre}
                onChange={(e) => {
                  const next = [...scenarios];
                  next[idx] = { ...next[idx], nombre: e.target.value };
                  setScenarios(next);
                }}
              />
              <label className={styles.scenarioSlider}>
                Cascada {(grad * 100).toFixed(0)}% / Rent. {((1 - grad) * 100).toFixed(0)}%
                <input
                  type="range"
                  min={0}
                  max={100}
                  value={grad * 100}
                  onChange={(e) => {
                    const g = Number(e.target.value) / 100;
                    const next = [...scenarios];
                    next[idx] = {
                      ...next[idx],
                      config: {
                        ...(next[idx].config ?? baseConfig),
                        weight_tasa_graduacion: g,
                        weight_eficiencia_operativa: Math.round((1 - g) * 100) / 100,
                      },
                    };
                    setScenarios(next);
                  }}
                />
              </label>
            </div>
          );
        })}
      </div>

      {error && <div className={styles.error}>{error}</div>}

      {!report && !error && (
        <div className={styles.placeholder}>
          <p>
            Configurá 2 o 3 escenarios y generá la comparativa para ver ingresos, completitud de
            aulas, alocación de docentes y demanda satisfecha lado a lado.
          </p>
        </div>
      )}

      {report && charts && (
        <>
          <Legend series={legend} />

          {/* KPIs rápidos por escenario */}
          <div className={styles.kpiGrid}>
            {report.escenarios.map((e, i) => (
              <div key={e.nombre} className={styles.kpiCard}>
                <div
                  className={styles.kpiHeader}
                  style={{ borderColor: SCENARIO_COLORS[i % SCENARIO_COLORS.length] }}
                >
                  {e.nombre}
                </div>
                <div className={styles.kpiRow}>
                  <span>Comisiones</span>
                  <strong>{e.metricas.comisiones_abiertas}</strong>
                </div>
                <div className={styles.kpiRow}>
                  <span>Ingresos</span>
                  <strong>{fmtMoney(e.metricas.ingresos_proyectados)}</strong>
                </div>
                <div className={styles.kpiRow}>
                  <span>Demanda satisfecha</span>
                  <strong>
                    {fmtInt(e.metricas.demanda_satisfecha)} / {fmtInt(e.metricas.demanda_total)}
                  </strong>
                </div>
                <div className={styles.kpiRow}>
                  <span>Docentes libres</span>
                  <strong>
                    {e.metricas.docentes_libres} / {e.metricas.docentes_totales}
                  </strong>
                </div>
              </div>
            ))}
          </div>

          {/* Reporte de ingresos */}
          <section className={styles.reportSection}>
            <h3 className={styles.reportTitle}>💰 Reporte de ingresos proyectados</h3>
            <p className={styles.reportHint}>
              Ingreso total por alumnos con cupo asignado, por escenario.
            </p>
            <GroupedBarChart
              categories={['Ingresos proyectados']}
              series={charts.ingresos}
              format={fmtMoney}
              unit=""
            />
          </section>

          {/* Reportes porcentuales agrupados */}
          <section className={styles.reportSection}>
            <h3 className={styles.reportTitle}>📈 Eficiencia operativa (%)</h3>
            <p className={styles.reportHint}>
              Completitud de aulas, alocación de docentes, demanda satisfecha y cobertura de
              materias críticas — todo en escala 0-100 para comparar de un vistazo.
            </p>
            <GroupedBarChart
              categories={['Demanda satisf.', 'Ocupación aulas', 'Docentes asign.', 'Cuellos cubiertos']}
              series={charts.porcentajes}
              format={(v) => `${v.toFixed(1)}%`}
              unit="%"
              height={300}
            />
          </section>

          {/* Gauges de alocación de docentes (uno por escenario) */}
          <section className={styles.reportSection}>
            <h3 className={styles.reportTitle}>👩‍🏫 Alocación de docentes</h3>
            <p className={styles.reportHint}>
              Idealmente ningún docente queda libre. El medidor muestra el % del pool asignado.
            </p>
            <div className={styles.gaugeRow}>
              {report.escenarios.map((e, i) => (
                <Gauge
                  key={e.nombre}
                  percent={e.metricas.pct_docentes_asignados}
                  label={`${e.nombre} · ${e.metricas.docentes_libres} libres`}
                  color={SCENARIO_COLORS[i % SCENARIO_COLORS.length]}
                />
              ))}
            </div>
          </section>

          {/* Diagnóstico de cuellos de recursos */}
          <section className={styles.reportSection}>
            <h3 className={styles.reportTitle}>🚧 Comisiones bloqueadas por falta de recursos</h3>
            <div className={styles.diagGrid}>
              {report.escenarios.map((e, i) => (
                <div key={e.nombre} className={styles.diagCard}>
                  <span
                    className={styles.kpiHeader}
                    style={{ borderColor: SCENARIO_COLORS[i % SCENARIO_COLORS.length] }}
                  >
                    {e.nombre}
                  </span>
                  <div className={styles.kpiRow}>
                    <span>Sin aula</span>
                    <strong>{e.metricas.comisiones_sin_aula}</strong>
                  </div>
                  <div className={styles.kpiRow}>
                    <span>Sin docente</span>
                    <strong>{e.metricas.comisiones_sin_docente}</strong>
                  </div>
                  <div className={styles.kpiRow}>
                    <span>Aulas usadas</span>
                    <strong>
                      {e.metricas.aulas_usadas} / {e.metricas.aulas_totales}
                    </strong>
                  </div>
                </div>
              ))}
            </div>
          </section>
        </>
      )}
    </div>
  );
};

export default ComparativeReportView;
