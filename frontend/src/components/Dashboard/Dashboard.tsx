import React, { useState, useEffect } from 'react';
import { kairosService } from '../../services/kairosService';
import type { Plan, Student, KairosConfig, PlanSummary } from '../../services/kairosService';
import GraphViewer from '../Graph/GraphViewer';
import PrescriptionTable from '../Prescriptions/PrescriptionTable';
import styles from './Dashboard.module.css';

const Dashboard: React.FC = () => {
  const [planes, setPlanes] = useState<PlanSummary[]>([]);
  const [selectedPlanCode, setSelectedPlanCode] = useState<string>('');
  const [plan, setPlan] = useState<Plan | null>(null);
  const [students, setStudents] = useState<Student[]>([]);
  const [results, setResults] = useState<any>(null);
  const [graphData, setGraphData] = useState<any>(null);
  const [activeTab, setActiveTab] = useState<'resultados' | 'grafo'>('resultados');
  const [loading, setLoading] = useState(false);
  const [bootstrapping, setBootstrapping] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [info, setInfo] = useState<string | null>(null);
  const [ingestBusy, setIngestBusy] = useState(false);
  const [config, setConfig] = useState<KairosConfig>({
    weight_tasa_graduacion: 0.7,
    weight_eficiencia_operativa: 0.3,
    min_tasa_ocupacion: 0.6,
    max_cupos_por_comision: 50,
    max_comisiones_a_abrir: null,
  });

  useEffect(() => {
    kairosService.getConfig().then(setConfig).catch(() => {});
  }, []);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const lista = await kairosService.listPlanes();
        if (cancelled) return;
        setPlanes(lista);
        if (lista.length > 0) {
          setSelectedPlanCode(lista[0].codigo_plan);
        } else {
          setBootstrapping(false);
        }
      } catch (err: any) {
        if (!cancelled) {
          setError(err.message || 'Error listando planes');
          setBootstrapping(false);
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (!selectedPlanCode) return;
    let cancelled = false;
    setBootstrapping(true);
    (async () => {
      try {
        const [p, ests] = await Promise.all([
          kairosService.getPlan(selectedPlanCode),
          kairosService.getEstudiantes(selectedPlanCode),
        ]);
        if (cancelled) return;
        setPlan(p);
        setStudents(ests);
        setResults(null);
        setGraphData(null);
      } catch (err: any) {
        if (!cancelled) setError(err.message || 'Error cargando datos del plan');
      } finally {
        if (!cancelled) setBootstrapping(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [selectedPlanCode]);

  const refreshPlanes = async (preferCodigo?: string): Promise<PlanSummary[]> => {
    const lista = await kairosService.listPlanes();
    setPlanes(lista);
    if (preferCodigo && lista.some(p => p.codigo_plan === preferCodigo)) {
      setSelectedPlanCode(preferCodigo);
    } else if (lista.length > 0 && !lista.some(p => p.codigo_plan === selectedPlanCode)) {
      setSelectedPlanCode(lista[0].codigo_plan);
    }
    return lista;
  };

  const readJsonFile = (file: File): Promise<any> =>
    new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = (e) => {
        try {
          resolve(JSON.parse(e.target?.result as string));
        } catch (err: any) {
          reject(new Error(`JSON invalido: ${err.message}`));
        }
      };
      reader.onerror = () => reject(new Error('No se pudo leer el archivo'));
      reader.readAsText(file);
    });

  const handlePlanUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    e.target.value = '';
    if (!file) return;

    setError(null);
    setInfo(null);
    setIngestBusy(true);
    try {
      const data = await readJsonFile(file);
      if (!data?.codigo_plan) {
        throw new Error('El JSON no parece un plan (falta codigo_plan)');
      }
      const cantidad = data.materias ? Object.keys(data.materias).length : 0;
      const existente = planes.find(p => p.codigo_plan === data.codigo_plan);
      const mensaje = existente
        ? `Vas a REEMPLAZAR el plan ${existente.codigo_plan} (${existente.nombre_carrera}, ${existente.cantidad_materias} materias) ` +
          `con el archivo "${file.name}":\n\n` +
          `  ${data.codigo_plan} - ${data.nombre_carrera ?? '(sin nombre)'} (${cantidad} materias)\n\n` +
          `¿Confirmar?`
        : `Vas a ingestar el plan:\n\n` +
          `  ${data.codigo_plan} - ${data.nombre_carrera ?? '(sin nombre)'} (${cantidad} materias)\n\n` +
          `Archivo: ${file.name}\n\n¿Confirmar?`;
      if (!window.confirm(mensaje)) {
        setIngestBusy(false);
        return;
      }
      const summary = await kairosService.ingestarPlan(data);
      await refreshPlanes(summary.codigo_plan);
      setInfo(`Plan ${summary.codigo_plan} ingestado (${summary.cantidad_materias} materias).`);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setIngestBusy(false);
    }
  };

  const handleEstudiantesUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    e.target.value = '';
    if (!file) return;

    setError(null);
    setInfo(null);
    setIngestBusy(true);
    try {
      const data = await readJsonFile(file);
      if (!Array.isArray(data)) {
        throw new Error('El JSON debe ser una lista de estudiantes');
      }
      const planesIds = Array.from(
        new Set(data.map((e: any) => e?.plan_estudio_id).filter(Boolean))
      );
      const planesStr = planesIds.length > 0 ? planesIds.join(', ') : '(sin plan_estudio_id)';
      const mensaje =
        `Vas a ingestar ${data.length} estudiantes del archivo "${file.name}".\n\n` +
        `Planes referenciados: ${planesStr}\n\n` +
        `Los estudiantes que ya existan (mismo estudiante_id) seran reemplazados.\n\n¿Confirmar?`;
      if (!window.confirm(mensaje)) {
        setIngestBusy(false);
        return;
      }
      const res = await kairosService.ingestarEstudiantes(data);
      let msg = `Estudiantes persistidos: ${res.persistidos} (rechazados: ${res.rechazados}).`;
      if (res.errores.length > 0) {
        msg += ` Detalles: ${res.errores.slice(0, 3).join('; ')}${res.errores.length > 3 ? '…' : ''}`;
      }
      setInfo(msg);
      if (selectedPlanCode) {
        const ests = await kairosService.getEstudiantes(selectedPlanCode);
        setStudents(ests);
      }
    } catch (err: any) {
      setError(err.message);
    } finally {
      setIngestBusy(false);
    }
  };

  const handleWeightChange = (graduacion: number) => {
    setConfig(prev => ({
      ...prev,
      weight_tasa_graduacion: graduacion,
      weight_eficiencia_operativa: Math.round((1 - graduacion) * 100) / 100,
    }));
  };

  const processData = async () => {
    if (!plan || !selectedPlanCode) {
      setError('Seleccioná un plan primero, che.');
      return;
    }

    setLoading(true);
    setError(null);
    try {
      const res = await kairosService.processFromDb(selectedPlanCode, config);
      setResults(res);

      const graph = await kairosService.getGraph(plan);
      setGraphData(graph);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className={styles.wrapper}>
      <header className={styles.header}>
        <h1 className={styles.logo}>KAIROS <span className={styles.tag}>ENGINE</span></h1>
        <div className={styles.controls}>
          <select
            className={styles.planSelect}
            value={selectedPlanCode}
            onChange={(e) => setSelectedPlanCode(e.target.value)}
            disabled={planes.length === 0 || bootstrapping}
          >
            {planes.length === 0 && <option value="">Sin planes en la DB</option>}
            {planes.map((p) => (
              <option key={p.codigo_plan} value={p.codigo_plan}>
                {p.nombre_carrera} ({p.cantidad_materias} materias)
              </option>
            ))}
          </select>
          <span className={styles.studentsBadge}>
            {bootstrapping ? 'Cargando…' : `${students.length} estudiantes`}
          </span>
          <button
            className={styles.processBtn}
            onClick={processData}
            disabled={loading || bootstrapping || !plan}
          >
            {loading ? 'Procesando...' : 'Prender Motor'}
          </button>
        </div>
      </header>

      {error && <div className={styles.error}>{error}</div>}
      {info && <div className={styles.info}>{info}</div>}

      <section className={styles.ingestPanel}>
        <h3 className={styles.configTitle}>Ingesta de datos</h3>
        <div className={styles.ingestRow}>
          <label className={styles.uploadBtn}>
            {ingestBusy ? 'Procesando…' : 'Importar Plan (JSON)'}
            <input
              type="file"
              accept=".json,application/json"
              onChange={handlePlanUpload}
              disabled={ingestBusy}
              hidden
            />
          </label>
          <label className={styles.uploadBtn}>
            {ingestBusy ? 'Procesando…' : 'Importar Estudiantes (JSON)'}
            <input
              type="file"
              accept=".json,application/json"
              onChange={handleEstudiantesUpload}
              disabled={ingestBusy}
              hidden
            />
          </label>
          <span className={styles.ingestHint}>
            Los archivos se persisten en la DB. Plan duplicado pide confirmación.
          </span>
        </div>
      </section>

      <section className={styles.configPanel}>
        <h3 className={styles.configTitle}>Panel de Configuración</h3>
        <div className={styles.sliderGroup}>
          <div className={styles.sliderRow}>
            <label>Cascada: <strong>{(config.weight_tasa_graduacion * 100).toFixed(0)}%</strong></label>
            <input
              type="range"
              min="0"
              max="100"
              value={config.weight_tasa_graduacion * 100}
              onChange={(e) => handleWeightChange(Number(e.target.value) / 100)}
              className={styles.slider}
            />
            <label>Rentabilidad: <strong>{(config.weight_eficiencia_operativa * 100).toFixed(0)}%</strong></label>
          </div>
          <p className={styles.sliderHint}>
            ← Prioriza materias que desbloquean la carrera | Prioriza comisiones que generan más ingreso →
          </p>
          <div className={styles.sliderRow}>
            <label>Score mínimo para abrir: <strong>{(config.min_tasa_ocupacion * 10).toFixed(1)}</strong></label>
            <input
              type="range"
              min="0"
              max="100"
              value={config.min_tasa_ocupacion * 100}
              onChange={(e) => setConfig(prev => ({ ...prev, min_tasa_ocupacion: Number(e.target.value) / 100 }))}
              className={styles.slider}
            />
          </div>
          <p className={styles.sliderHint}>
            Solo se abren comisiones con score mayor a este valor
          </p>
          <div className={styles.sliderRow}>
            <label>Presupuesto (max comisiones): <strong>{config.max_comisiones_a_abrir ?? 'Sin límite'}</strong></label>
            <input
              type="range"
              min="1"
              max="52"
              value={config.max_comisiones_a_abrir ?? 52}
              onChange={(e) => {
                const val = Number(e.target.value);
                setConfig(prev => ({ ...prev, max_comisiones_a_abrir: val >= 52 ? null : val }));
              }}
              className={styles.slider}
            />
          </div>
          <p className={styles.sliderHint}>
            Tope máximo de comisiones que la universidad puede abrir este cuatrimestre
          </p>
        </div>
      </section>

      <main className={styles.content}>
        {results ? (
          <>
            <div className={styles.tabs} role="tablist">
              <button
                role="tab"
                aria-selected={activeTab === 'resultados'}
                className={`${styles.tab} ${activeTab === 'resultados' ? styles.tabActive : ''}`}
                onClick={() => setActiveTab('resultados')}
              >
                Resultados
              </button>
              <button
                role="tab"
                aria-selected={activeTab === 'grafo'}
                className={`${styles.tab} ${activeTab === 'grafo' ? styles.tabActive : ''}`}
                onClick={() => setActiveTab('grafo')}
                disabled={!graphData}
              >
                Mapa de Correlatividades
              </button>
            </div>

            {activeTab === 'resultados' && (
              <>
                <section className={styles.stats}>
                  <div className={styles.statCard} title="Suma total de inscripciones necesarias. Si un alumno necesita 3 materias en distintos turnos, suma 3.">
                    <span className={styles.statLabel}>Demanda Total</span>
                    <span className={styles.statValue}>{results.demanda_total}</span>
                  </div>
                  <div className={styles.statCard} title="Cantidad de comisiones (materia+turno) que el motor recomienda abrir con los parámetros actuales.">
                    <span className={styles.statLabel}>Materias a Abrir</span>
                    <span className={styles.statValue}>
                      {Object.values(results.prescripciones).filter((p: any) => p.decision === 'ABRIR').length}
                    </span>
                  </div>
                  <div className={styles.statCard} title="Materias que si no se abren, traban a muchos alumnos porque tienen muchas materias que dependen de ellas.">
                    <span className={styles.statLabel}>Cuellos de Botella</span>
                    <span className={styles.statValue}>{results.cuellos_botella.length}</span>
                  </div>
                </section>

                <div className={styles.bottlenecks}>
                  <h3 className={styles.subTitle}>Materias Críticas</h3>
                  <div className={styles.bottleneckGrid}>
                    {results.cuellos_botella.map((c: any) => (
                      <div key={c.codigo} className={styles.bottleneckItem}>
                        <span className={styles.bCode}>{c.codigo}</span>
                        <span className={styles.bName}>{c.nombre}</span>
                        <span className={styles.bLevel}>{c.criticidad}</span>
                      </div>
                    ))}
                  </div>
                </div>

                <PrescriptionTable prescriptions={results.prescripciones} weightCascada={config.weight_tasa_graduacion} weightRentabilidad={config.weight_eficiencia_operativa} />
              </>
            )}

            {activeTab === 'grafo' && graphData && (
              <div className={styles.graphFull}>
                <GraphViewer data={graphData} />
              </div>
            )}
          </>
        ) : (
          <div className={styles.empty}>
            <h2>Listo para optimizar.</h2>
            <p>{bootstrapping ? 'Cargando datos desde la DB…' : 'Dale al botón de "Prender Motor".'}</p>
          </div>
        )}
      </main>
    </div>
  );
};

export default Dashboard;
