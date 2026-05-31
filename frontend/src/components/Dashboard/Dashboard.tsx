import React, { useState } from 'react';
import { kairosService } from '../../services/kairosService';
import type { Plan, Student } from '../../services/kairosService';
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

  const processData = async () => {
    if (!plan || students.length === 0) {
      setError('Cargá el plan y los estudiantes primero, che.');
      return;
    }

    setLoading(true);
    setError(null);
    try {
      const res = await kairosService.processDemanda({ plan, estudiantes: students });
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
          <label className={styles.uploadBtn}>
            Plan (JSON)
            <input type="file" accept=".json" onChange={(e) => handleFileUpload(e, 'plan')} hidden />
          </label>
          <label className={styles.uploadBtn}>
            Estudiantes (JSON)
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
