import React, { useEffect, useMemo, useRef, useState } from 'react';
import { authService, rolLabel } from '../../services/authService';
import type { CreateUserPayload, Rol, User } from '../../services/authService';
import { useAuth } from '../../context/AuthContext';
import styles from './AdminPanel.module.css';

type RolFilter = 'todos' | Rol;

const ROLES: Rol[] = ['docente_funcional', 'director_departamento', 'decano'];

const AdminPanel: React.FC = () => {
  const { user, token, logout } = useAuth();

  const [users, setUsers] = useState<User[]>([]);
  const [loadingList, setLoadingList] = useState(true);
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  const [search, setSearch] = useState('');
  const [rolFilter, setRolFilter] = useState<RolFilter>('todos');

  const [formOpen, setFormOpen] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const [formUsername, setFormUsername] = useState('');
  const [formPassword, setFormPassword] = useState('');
  const [formNombre, setFormNombre] = useState('');
  const [formRol, setFormRol] = useState<Rol>('docente_funcional');

  // guardamos el timer del toast para limpiarlo si llegan varios éxitos seguidos
  const toastTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const fetchUsers = async () => {
    if (!token) return;
    setLoadingList(true);
    setError(null);
    try {
      const list = await authService.listUsers(token);
      setUsers(list);
    } catch (err: any) {
      const msg: string = err?.message || 'Error listando usuarios';
      setError(msg);
      // si el back nos dice que la sesión expiró, deslogueamos
      if (/sesi[oó]n expirada/i.test(msg)) {
        logout();
      }
    } finally {
      setLoadingList(false);
    }
  };

  useEffect(() => {
    fetchUsers();
    return () => {
      if (toastTimerRef.current) clearTimeout(toastTimerRef.current);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const showSuccess = (msg: string) => {
    setSuccessMsg(msg);
    if (toastTimerRef.current) clearTimeout(toastTimerRef.current);
    toastTimerRef.current = setTimeout(() => setSuccessMsg(null), 3000);
  };

  const resetForm = () => {
    setFormUsername('');
    setFormPassword('');
    setFormNombre('');
    setFormRol('docente_funcional');
    setFormError(null);
  };

  const toggleForm = () => {
    if (formOpen) {
      resetForm();
      setFormOpen(false);
    } else {
      setFormOpen(true);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!token) return;

    const username = formUsername.trim();
    const password = formPassword;
    const nombre = formNombre.trim();

    if (!username || !password || !nombre) {
      setFormError('Completá todos los campos antes de crear el usuario.');
      return;
    }

    const payload: CreateUserPayload = {
      username,
      password,
      nombre,
      rol: formRol,
    };

    setCreating(true);
    setFormError(null);
    try {
      const created = await authService.createUser(token, payload);
      showSuccess(`Usuario ${created.username} creado correctamente`);
      resetForm();
      setFormOpen(false);
      await fetchUsers();
    } catch (err: any) {
      setFormError(err?.message || 'Error creando usuario');
    } finally {
      setCreating(false);
    }
  };

  const filteredUsers = useMemo(() => {
    const q = search.trim().toLowerCase();
    return users.filter((u) => {
      if (rolFilter !== 'todos' && u.rol !== rolFilter) return false;
      if (!q) return true;
      return (
        u.username.toLowerCase().includes(q) ||
        u.nombre.toLowerCase().includes(q)
      );
    });
  }, [users, search, rolFilter]);

  return (
    <div className={styles.wrapper}>
      {successMsg && <div className={styles.toast}>{successMsg}</div>}

      <div className={styles.headerBar}>
        <div className={styles.headerLeft}>
          <span className={styles.title}>Administración de usuarios</span>
          <span className={styles.subtitle}>
            Listá y creá usuarios del sistema. Solo accesible para decanos.
          </span>
        </div>

        <div className={styles.filtersRow}>
          <input
            type="text"
            className={styles.searchInput}
            placeholder="Buscar por usuario o nombre…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
          <select
            className={styles.roleSelect}
            value={rolFilter}
            onChange={(e) => setRolFilter(e.target.value as RolFilter)}
          >
            <option value="todos">Todos los roles</option>
            {ROLES.map((r) => (
              <option key={r} value={r}>
                {rolLabel(r)}
              </option>
            ))}
          </select>
          <button
            type="button"
            className={`${styles.newBtn} ${formOpen ? styles.cancelBtn : ''}`}
            onClick={toggleForm}
          >
            {formOpen ? 'Cancelar' : '+ Nuevo usuario'}
          </button>
        </div>
      </div>

      {error && <div className={styles.errorBanner}>{error}</div>}

      {formOpen && (
        <form className={styles.formCard} onSubmit={handleSubmit}>
          <span className={styles.formTitle}>Nuevo usuario</span>
          {formError && <div className={styles.formError}>{formError}</div>}
          <div className={styles.formGrid}>
            <div className={styles.field}>
              <label className={styles.label} htmlFor="adm-username">Username</label>
              <input
                id="adm-username"
                className={styles.input}
                type="text"
                value={formUsername}
                onChange={(e) => setFormUsername(e.target.value)}
                disabled={creating}
                autoComplete="off"
              />
            </div>
            <div className={styles.field}>
              <label className={styles.label} htmlFor="adm-password">Contraseña</label>
              <input
                id="adm-password"
                className={styles.input}
                type="password"
                value={formPassword}
                onChange={(e) => setFormPassword(e.target.value)}
                disabled={creating}
                autoComplete="new-password"
              />
            </div>
            <div className={styles.field}>
              <label className={styles.label} htmlFor="adm-nombre">Nombre completo</label>
              <input
                id="adm-nombre"
                className={styles.input}
                type="text"
                value={formNombre}
                onChange={(e) => setFormNombre(e.target.value)}
                disabled={creating}
                autoComplete="off"
              />
            </div>
            <div className={styles.field}>
              <label className={styles.label} htmlFor="adm-rol">Rol</label>
              <select
                id="adm-rol"
                className={styles.input}
                value={formRol}
                onChange={(e) => setFormRol(e.target.value as Rol)}
                disabled={creating}
              >
                {ROLES.map((r) => (
                  <option key={r} value={r}>
                    {rolLabel(r)}
                  </option>
                ))}
              </select>
            </div>
          </div>
          <div className={styles.formActions}>
            <button type="submit" className={styles.submitBtn} disabled={creating}>
              {creating ? 'Creando…' : 'Crear usuario'}
            </button>
          </div>
        </form>
      )}

      <div className={styles.tableWrapper}>
        {loadingList ? (
          <div className={styles.loading}>Cargando usuarios…</div>
        ) : filteredUsers.length === 0 ? (
          <div className={styles.empty}>
            No hay usuarios que coincidan con los filtros
          </div>
        ) : (
          <table className={styles.table}>
            <thead>
              <tr>
                <th>ID</th>
                <th>Username</th>
                <th>Nombre</th>
                <th>Rol</th>
              </tr>
            </thead>
            <tbody>
              {filteredUsers.map((u) => {
                const isMe = user != null && String(u.id) === String(user.id);
                return (
                  <tr key={u.id}>
                    <td className={styles.idCell}>{u.id}</td>
                    <td>
                      <div className={styles.usernameCell}>
                        <span>{u.username}</span>
                        {isMe && <span className={styles.meChip}>Yo</span>}
                      </div>
                    </td>
                    <td>{u.nombre}</td>
                    <td>{rolLabel(u.rol)}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
};

export default AdminPanel;
