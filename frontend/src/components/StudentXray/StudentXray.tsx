import React, { useState } from 'react';
import { kairosService } from '../../services/kairosService';
import type { StudentXray as StudentXrayData } from '../../services/kairosService';
import styles from './StudentXray.module.css';

const cuatriLabel = (ano: number, cuatri: number) => `${ano}° año · ${cuatri}° cuat.`;

const StudentXray: React.FC = () => {
  const [legajo, setLegajo] = useState('');
  const [xray, setXray] = useState<StudentXrayData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const buscar = async () => {
    const id = legajo.trim();
    if (!id) return;
    setLoading(true);
    setError(null);
    try {
      const data = await kairosService.getRadiografia(id);
      setXray(data);
    } catch (err: any) {
      setXray(null);
      setError(err.message || 'No se pudo obtener la radiografía');
    } finally {
      setLoading(false);
    }
  };

  const onKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') buscar();
  };

  return (
    <div className={styles.container}>
      <div className={styles.searchBar}>
        <span className={styles.searchLabel}>Legajo del alumno</span>
        <input
          className={styles.input}
          value={legajo}
          onChange={(e) => setLegajo(e.target.value)}
          onKeyDown={onKeyDown}
          placeholder="Ej: EST0007"
          aria-label="Legajo del alumno"
        />
        <button className={styles.searchBtn} onClick={buscar} disabled={loading || !legajo.trim()}>
          {loading ? 'Buscando…' : 'Radiografiar'}
        </button>
        <span className={styles.hint}>
          Ingresá un legajo y mirá qué le conviene cursar según sus correlativas.
        </span>
      </div>

      {error && <div className={styles.error}>{error}</div>}

      {!xray && !error && (
        <div className={styles.empty}>
          <h2>Radiografía académica</h2>
          <p>Buscá un legajo para ver en qué está parado el alumno.</p>
        </div>
      )}

      {xray && (
        <>
          <div className={styles.summaryHeader}>
            <span className={styles.studentId}>{xray.estudiante_id}</span>
            <span className={styles.carrera}>{xray.carrera} · Plan {xray.plan}</span>
          </div>

          <div className={styles.progressWrap}>
            <div className={styles.progressTop}>
              <span>
                Avance de carrera: {xray.resumen.aprobadas} de {xray.resumen.total_materias} materias aprobadas
              </span>
              <span className={styles.progressPct}>{xray.resumen.porcentaje_avance}%</span>
            </div>
            <div className={styles.progressBar}>
              <div
                className={styles.progressFill}
                style={{ width: `${xray.resumen.porcentaje_avance}%` }}
              />
            </div>
          </div>

          <div className={styles.counters}>
            <div className={styles.counter}>
              <span className={`${styles.counterValue} ${styles.cAprobadas}`}>{xray.resumen.aprobadas}</span>
              <span className={styles.counterLabel}>Aprobadas</span>
            </div>
            <div className={styles.counter}>
              <span className={`${styles.counterValue} ${styles.cPendientes}`}>{xray.resumen.pendientes_de_final}</span>
              <span className={styles.counterLabel}>Pendientes de final</span>
            </div>
            <div className={styles.counter}>
              <span className={`${styles.counterValue} ${styles.cDisponibles}`}>{xray.resumen.disponibles_a_cursar}</span>
              <span className={styles.counterLabel}>Disponibles a cursar</span>
            </div>
            <div className={styles.counter}>
              <span className={`${styles.counterValue} ${styles.cBloqueadas}`}>{xray.resumen.bloqueadas}</span>
              <span className={styles.counterLabel}>Bloqueadas</span>
            </div>
          </div>

          <div className={styles.buckets}>
            {/* Disponibles a cursar: lo más accionable, primero. */}
            <section className={styles.bucket}>
              <h3 className={styles.bucketTitle}>
                <span>✅ Disponibles a cursar</span>
                <span className={styles.bucketCount}>{xray.disponibles_a_cursar.length}</span>
              </h3>
              {xray.disponibles_a_cursar.length === 0 ? (
                <p className={styles.bucketEmpty}>No hay materias habilitadas ahora mismo.</p>
              ) : (
                <ul className={styles.subjectList}>
                  {xray.disponibles_a_cursar.map((m, i) => (
                    <li
                      key={m.codigo}
                      className={`${styles.subject} ${i === 0 ? styles.subjectRecommended : ''}`}
                    >
                      <div className={styles.subjectHead}>
                        <span className={styles.subjectCode}>{m.codigo}</span>
                        <span className={styles.subjectName}>{m.nombre}</span>
                        <span className={styles.subjectMeta}>{cuatriLabel(m.ano, m.cuatrimestre)}</span>
                      </div>
                      {m.impacto_cascada > 0 && (
                        <span className={`${styles.tag} ${styles.tagInfo}`}>
                          Desbloquea {m.impacto_cascada} materia{m.impacto_cascada === 1 ? '' : 's'}
                        </span>
                      )}
                      {m.final_condicionado && (
                        <span className={`${styles.tag} ${styles.tagWarn}`}>
                          Final condicionado: aprobá {m.correlativas_a_aprobar_para_final.join(', ')}
                        </span>
                      )}
                    </li>
                  ))}
                </ul>
              )}
            </section>

            {/* Pendientes de final */}
            <section className={styles.bucket}>
              <h3 className={styles.bucketTitle}>
                <span>📝 Pendientes de final</span>
                <span className={styles.bucketCount}>{xray.pendientes_de_final.length}</span>
              </h3>
              {xray.pendientes_de_final.length === 0 ? (
                <p className={styles.bucketEmpty}>Sin finales pendientes.</p>
              ) : (
                <ul className={styles.subjectList}>
                  {xray.pendientes_de_final.map((m) => (
                    <li key={m.codigo} className={styles.subject}>
                      <div className={styles.subjectHead}>
                        <span className={styles.subjectCode}>{m.codigo}</span>
                        <span className={styles.subjectName}>{m.nombre}</span>
                        <span className={styles.subjectMeta}>{cuatriLabel(m.ano, m.cuatrimestre)}</span>
                      </div>
                      {m.puede_rendir_final ? (
                        <span className={`${styles.tag} ${styles.tagOk}`}>Puede rendir el final</span>
                      ) : (
                        <span className={`${styles.tag} ${styles.tagWarn}`}>
                          Primero aprobá {m.correlativas_faltantes_final.join(', ')}
                        </span>
                      )}
                    </li>
                  ))}
                </ul>
              )}
            </section>

            {/* Bloqueadas */}
            <section className={styles.bucket}>
              <h3 className={styles.bucketTitle}>
                <span>🔒 Bloqueadas</span>
                <span className={styles.bucketCount}>{xray.bloqueadas.length}</span>
              </h3>
              {xray.bloqueadas.length === 0 ? (
                <p className={styles.bucketEmpty}>Nada bloqueado. 🎉</p>
              ) : (
                <ul className={styles.subjectList}>
                  {xray.bloqueadas.map((m) => (
                    <li key={m.codigo} className={styles.subject}>
                      <div className={styles.subjectHead}>
                        <span className={styles.subjectCode}>{m.codigo}</span>
                        <span className={styles.subjectName}>{m.nombre}</span>
                        <span className={styles.subjectMeta}>{cuatriLabel(m.ano, m.cuatrimestre)}</span>
                      </div>
                      <span className={`${styles.tag} ${styles.tagBlocked}`}>
                        Falta regularizar {m.correlativas_faltantes.join(', ')}
                      </span>
                    </li>
                  ))}
                </ul>
              )}
            </section>

            {/* Aprobadas */}
            <section className={styles.bucket}>
              <h3 className={styles.bucketTitle}>
                <span>🎓 Aprobadas</span>
                <span className={styles.bucketCount}>{xray.aprobadas.length}</span>
              </h3>
              {xray.aprobadas.length === 0 ? (
                <p className={styles.bucketEmpty}>Todavía no aprobó materias.</p>
              ) : (
                <ul className={styles.subjectList}>
                  {xray.aprobadas.map((m) => (
                    <li key={m.codigo} className={styles.subject}>
                      <div className={styles.subjectHead}>
                        <span className={styles.subjectCode}>{m.codigo}</span>
                        <span className={styles.subjectName}>{m.nombre}</span>
                        <span className={styles.subjectMeta}>{cuatriLabel(m.ano, m.cuatrimestre)}</span>
                      </div>
                    </li>
                  ))}
                </ul>
              )}
            </section>
          </div>
        </>
      )}
    </div>
  );
};

export default StudentXray;
