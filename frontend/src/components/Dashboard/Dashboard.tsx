import React, { useState } from 'react';
import { kairosService } from '../../services/kairosService';
import type { Plan, Student, KairosConfig } from '../../services/kairosService';
import GraphViewer from '../Graph/GraphViewer';
import PrescriptionTable from '../Prescriptions/PrescriptionTable';
import styles from './Dashboard.module.css';

const Dashboard: React.FC = () => {
  const [plan, setPlan] = useState<Plan | null>(null);
  const [students, setStudents] = useState<Student[]>([]);
  const [results, setResults] = useState<any>(null);
  const [graphData, setGraphData] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [config, setConfig] = useState<KairosConfig>({
    weight_tasa_graduacion: 0.7,
    weight_eficiencia_operativa: 0.3,
    min_tasa_ocupacion: 0.6,
    max_cupos_por_comision: 50,
    max_comisiones_a_abrir: null,
  });

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>, type: 'plan' | 'students') => {
    const file = e.target.files?.[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = (event) => {
      try {
        const content = event.target?.result as string;
        if (type === 'plan') {
          setPlan(JSON.parse(content));
        } else {
          // Para simplificar, asumimos que el CSV de estudiantes se parsea basicamenet o se manda crudo
          // En un caso real usariamos papaparse. Aqui simulamos carga de JSON para probar flujo.
          setStudents(JSON.parse(content));
        }
      } catch (err) {
        setError(`Error parseando el archivo ${type}. Asegurate que sea JSON.`);
      }
    };
    reader.readAsText(file);
  };

  const handleWeightChange = (graduacion: number) => {
    setConfig(prev => ({
      ...prev,
      weight_tasa_graduacion: graduacion,
      weight_eficiencia_operativa: Math.round((1 - graduacion) * 100) / 100,
    }));
  };

  const processData = async () => {
    if (!plan || students.length === 0) {
      setError('Cargá el plan y los estudiantes primero, che.');
      return;
    }

    setLoading(true);
    setError(null);
    try {
      const res = await kairosService.processDemanda({ plan, estudiantes: students, config });
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
          <label className={`${styles.uploadBtn} ${plan ? styles.uploadLoaded : ''}`}>
            {plan ? `Plan cargado (${Object.keys(plan.materias).length} materias)` : 'Plan (JSON)'}
            <input type="file" accept=".json" onChange={(e) => handleFileUpload(e, 'plan')} hidden />
          </label>
          <label className={`${styles.uploadBtn} ${students.length > 0 ? styles.uploadLoaded : ''}`}>
            {students.length > 0 ? `${students.length} estudiantes cargados` : 'Estudiantes (JSON)'}
            <input type="file" accept=".json" onChange={(e) => handleFileUpload(e, 'students')} hidden />
          </label>
          <button
            className={styles.processBtn}
            onClick={processData}
            disabled={loading || !plan || students.length === 0}
          >
            {loading ? 'Procesando...' : 'Prender Motor'}
          </button>
        </div>
      </header>

      {error && <div className={styles.error}>{error}</div>}

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
            <label>Exigencia para abrir: <strong>{(config.min_tasa_ocupacion * 100).toFixed(0)}%</strong></label>
            <input
              type="range"
              min="10"
              max="100"
              value={config.min_tasa_ocupacion * 100}
              onChange={(e) => setConfig(prev => ({ ...prev, min_tasa_ocupacion: Number(e.target.value) / 100 }))}
              className={styles.slider}
            />
          </div>
          <p className={styles.sliderHint}>
            Qué porcentaje del score máximo debe tener una materia para ser abierta
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
            <section className={styles.stats}>
              <div className={styles.statCard}>
                <span className={styles.statLabel}>Demanda Total</span>
                <span className={styles.statValue}>{results.demanda_total}</span>
              </div>
              <div className={styles.statCard}>
                <span className={styles.statLabel}>Materias a Abrir</span>
                <span className={styles.statValue}>
                  {Object.values(results.prescripciones).filter((p: any) => p.decision === 'ABRIR').length}
                </span>
              </div>
              <div className={styles.statCard}>
                <span className={styles.statLabel}>Cuellos de Botella</span>
                <span className={styles.statValue}>{results.cuellos_botella.length}</span>
              </div>
            </section>

            <div className={styles.grid}>
              <div className={styles.mainCol}>
                <PrescriptionTable prescriptions={results.prescripciones} />
              </div>
              <div className={styles.sideCol}>
                {graphData && <GraphViewer data={graphData} />}
                <div className={styles.bottlenecks}>
                  <h3 className={styles.subTitle}>Materias Críticas</h3>
                  {results.cuellos_botella.map((c: any) => (
                    <div key={c.codigo} className={styles.bottleneckItem}>
                      <span className={styles.bCode}>{c.codigo}</span>
                      <span className={styles.bName}>{c.nombre}</span>
                      <span className={styles.bLevel}>{c.criticidad}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </>
        ) : (
          <div className={styles.empty}>
            <h2>Listo para optimizar.</h2>
            <p>Subí los archivos y dale al botón de "Prender Motor".</p>
          </div>
        )}
      </main>
    </div>
  );
};

export default Dashboard;
