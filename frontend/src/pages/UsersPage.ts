import { userService, UserItem } from "../services/userService";
import { renderPagination } from "../components/Pagination";
import { Toast } from "../components/Toast";

export async function renderUsersPage(container: HTMLElement): Promise<void> {
  container.innerHTML = `
    <div class="page-container" style="max-width: 1400px; margin: 0 auto; padding: 1.5rem;">
      <!-- Header -->
      <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 2rem; flex-wrap: wrap; gap: 1rem;">
        <div>
          <div style="font-size: 0.8rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.08em; color: #38BDF8; margin-bottom: 0.35rem;">
            Control de Acceso y Gobernanza (RBAC)
          </div>
          <h1 style="font-size: 1.75rem; font-weight: 700; color: var(--text-primary); margin: 0;">
            Administración de Usuarios y Roles
          </h1>
          <p style="font-size: 0.9rem; color: var(--text-secondary); margin-top: 0.25rem;">
            Gestión centralizada de cuentas de funcionarios, auditores y privilegios del sistema.
          </p>
        </div>

        <button id="btn-open-create-user" class="btn btn-primary btn-sm" style="display: inline-flex; align-items: center; gap: 0.4rem;">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M16 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="8.5" cy="7" r="4"/><line x1="20" y1="8" x2="20" y2="14"/><line x1="23" y1="11" x2="17" y2="11"/></svg>
          Nuevo Usuario
        </button>
      </div>

      <!-- Users Table Card -->
      <div class="card" style="overflow: hidden; margin-bottom: 1.5rem;">
        <div style="overflow-x: auto;">
          <table style="width: 100%; border-collapse: collapse; font-size: 0.875rem;">
            <thead>
              <tr style="background: var(--bg-surface-elevated); color: var(--text-muted); font-size: 0.75rem; text-transform: uppercase;">
                <th style="padding: 0.75rem 1.25rem; text-align: left;">Funcionario / Correo</th>
                <th style="padding: 0.75rem 1rem; text-align: left;">Rol Asignado</th>
                <th style="padding: 0.75rem 1rem; text-align: center;">Estado</th>
                <th style="padding: 0.75rem 1rem; text-align: left;">Fecha de Registro</th>
                <th style="padding: 0.75rem 1.25rem; text-align: right;">Acciones</th>
              </tr>
            </thead>
            <tbody id="users-table-body">
              <tr>
                <td colspan="5" style="text-align: center; padding: 3rem; color: var(--text-muted);">
                  <div class="spinner" style="margin-right: 0.5rem;"></div> Cargando usuarios...
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- Pagination -->
      <div id="users-pagination"></div>

      <!-- Create User Modal -->
      <div id="create-user-modal-backdrop" style="display: none; position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0, 0, 0, 0.75); backdrop-filter: blur(4px); z-index: 100; align-items: center; justify-content: center; padding: 1.5rem;">
        <div class="card card-elevated" style="width: 100%; max-width: 480px; padding: 2rem; background: #0F172A; border: 1px solid var(--border-subtle);">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1.5rem;">
            <h2 style="font-size: 1.2rem; font-weight: 700; color: var(--text-primary); margin: 0;">
              Registrar Nuevo Usuario
            </h2>
            <button id="btn-close-create-user" class="btn btn-outline btn-sm" style="padding: 0.25rem 0.6rem;">&times;</button>
          </div>

          <form id="create-user-form">
            <div class="form-group" style="margin-bottom: 1.1rem;">
              <label class="form-label" style="display: block; font-size: 0.825rem; font-weight: 600; color: var(--text-secondary); margin-bottom: 0.35rem;">
                Nombre Completo
              </label>
              <input id="new-user-fullname" type="text" class="form-control" required placeholder="Ej. Ana Milena Gómez" style="width: 100%; padding: 0.6rem 0.8rem; background: #0B1120; border: 1px solid var(--border-subtle); color: #FFF; border-radius: var(--radius-sm);" />
            </div>

            <div class="form-group" style="margin-bottom: 1.1rem;">
              <label class="form-label" style="display: block; font-size: 0.825rem; font-weight: 600; color: var(--text-secondary); margin-bottom: 0.35rem;">
                Correo Electrónico Institucional
              </label>
              <input id="new-user-email" type="email" class="form-control" required placeholder="ejemplo@entidad.gov.co" style="width: 100%; padding: 0.6rem 0.8rem; background: #0B1120; border: 1px solid var(--border-subtle); color: #FFF; border-radius: var(--radius-sm);" />
            </div>

            <div class="form-group" style="margin-bottom: 1.1rem;">
              <label class="form-label" style="display: block; font-size: 0.825rem; font-weight: 600; color: var(--text-secondary); margin-bottom: 0.35rem;">
                Rol de Seguridad (RBAC)
              </label>
              <select id="new-user-role" class="form-control" style="width: 100%; padding: 0.6rem 0.8rem; background: #0B1120; border: 1px solid var(--border-subtle); color: #FFF; border-radius: var(--radius-sm);">
                <option value="CONSULTOR">CONSULTOR (Solo lectura y búsqueda)</option>
                <option value="REVISOR">REVISOR (Supervisión y corrección HITL)</option>
                <option value="GESTOR">GESTOR (Carga, extracción y reportes)</option>
                <option value="ADMIN">ADMIN (Control total y gobernanza)</option>
              </select>
            </div>

            <div class="form-group" style="margin-bottom: 1.5rem;">
              <label class="form-label" style="display: block; font-size: 0.825rem; font-weight: 600; color: var(--text-secondary); margin-bottom: 0.35rem;">
                Contraseña Temporal
              </label>
              <input id="new-user-password" type="password" class="form-control" required placeholder="Mínimo 8 caracteres" style="width: 100%; padding: 0.6rem 0.8rem; background: #0B1120; border: 1px solid var(--border-subtle); color: #FFF; border-radius: var(--radius-sm);" />
            </div>

            <div style="display: flex; gap: 0.75rem; justify-content: flex-end;">
              <button type="button" id="btn-cancel-create-user" class="btn btn-outline btn-sm">Cancelar</button>
              <button type="submit" id="btn-submit-create-user" class="btn btn-primary btn-sm">Crear Usuario</button>
            </div>
          </form>
        </div>
      </div>
    </div>
  `;

  let currentPage = 1;
  const pageSize = 10;

  // Setup Modal Controls
  setupUserModal(container, () => loadUsers(container, currentPage, pageSize));

  // Initial Fetch
  await loadUsers(container, currentPage, pageSize);
}

async function loadUsers(container: HTMLElement, page: number, pageSize: number): Promise<void> {
  const tbody = container.querySelector("#users-table-body");
  if (!tbody) return;

  try {
    const res = await userService.listUsers({ page, page_size: pageSize });

    if (!res.items || res.items.length === 0) {
      tbody.innerHTML = `<tr><td colspan="5" style="text-align: center; padding: 2rem; color: var(--text-muted);">No hay usuarios registrados.</td></tr>`;
      renderPagination("users-pagination", 1, 0, 0, () => {});
      return;
    }

    tbody.innerHTML = res.items.map((u: UserItem) => `
      <tr style="border-bottom: 1px solid var(--border-subtle); transition: background var(--transition-fast);">
        <td style="padding: 0.85rem 1.25rem;">
          <div style="font-weight: 600; color: var(--text-primary);">${u.full_name || u.email}</div>
          <div style="font-size: 0.75rem; color: var(--text-muted); font-family: var(--font-mono);">${u.email}</div>
        </td>
        <td style="padding: 0.85rem 1rem;">
          <span class="badge" style="background: rgba(2, 132, 199, 0.15); color: #38BDF8; font-weight: 600;">
            ${u.role}
          </span>
        </td>
        <td style="padding: 0.85rem 1rem; text-align: center;">
          <span class="badge badge-${u.is_active ? 'success' : 'danger'}">
            ${u.is_active ? 'Activo' : 'Inactivo'}
          </span>
        </td>
        <td style="padding: 0.85rem 1rem; font-size: 0.8rem; color: var(--text-muted);">
          ${new Date(u.created_at).toLocaleDateString("es-CO", { year: "numeric", month: "short", day: "numeric" })}
        </td>
        <td style="padding: 0.85rem 1.25rem; text-align: right;">
          ${u.is_active ? `
            <button class="btn btn-outline btn-sm btn-deactivate-user" data-id="${u.id}" data-name="${u.full_name || u.email}" style="color: #F87171; font-size: 0.75rem; padding: 0.2rem 0.6rem;">
              Desactivar
            </button>
          ` : `
            <span style="font-size: 0.75rem; color: var(--text-muted);">Desactivado</span>
          `}
        </td>
      </tr>
    `).join("");

    // Wire Deactivate Buttons
    tbody.querySelectorAll(".btn-deactivate-user").forEach((btn) => {
      btn.addEventListener("click", async () => {
        const id = (btn as HTMLElement).dataset.id!;
        const name = (btn as HTMLElement).dataset.name!;
        if (confirm(`¿Está seguro de desactivar la cuenta del usuario "${name}"?`)) {
          try {
            await userService.deactivateUser(id);
            Toast.success(`Usuario ${name} desactivado.`);
            loadUsers(container, page, pageSize);
          } catch (err: any) {
            Toast.error(err.message || "Error al desactivar usuario.");
          }
        }
      });
    });

    // Wire Pagination
    renderPagination(
      "users-pagination",
      res.page,
      res.page_size ? Math.ceil(res.total / res.page_size) : 1,
      res.total,
      (newPage) => loadUsers(container, newPage, pageSize)
    );
  } catch (err: any) {
    tbody.innerHTML = `<tr><td colspan="5" style="color: var(--color-danger); text-align: center; padding: 2rem;">Error al cargar usuarios: ${err.message || "Fallo"}</td></tr>`;
    Toast.error("Error al obtener listado de usuarios.");
  }
}

function setupUserModal(container: HTMLElement, onSuccess: () => void): void {
  const modal = container.querySelector("#create-user-modal-backdrop") as HTMLElement;
  const openBtn = container.querySelector("#btn-open-create-user");
  const closeBtn = container.querySelector("#btn-close-create-user");
  const cancelBtn = container.querySelector("#btn-cancel-create-user");
  const form = container.querySelector("#create-user-form") as HTMLFormElement;

  const openModal = () => { modal.style.display = "flex"; };
  const closeModal = () => { modal.style.display = "none"; form.reset(); };

  openBtn?.addEventListener("click", openModal);
  closeBtn?.addEventListener("click", closeModal);
  cancelBtn?.addEventListener("click", closeModal);

  form?.addEventListener("submit", async (e) => {
    e.preventDefault();
    const fullName = (container.querySelector("#new-user-fullname") as HTMLInputElement).value.trim();
    const email = (container.querySelector("#new-user-email") as HTMLInputElement).value.trim();
    const role = (container.querySelector("#new-user-role") as HTMLSelectElement).value;
    const password = (container.querySelector("#new-user-password") as HTMLInputElement).value;

    const submitBtn = container.querySelector("#btn-submit-create-user") as HTMLButtonElement;
    submitBtn.disabled = true;
    submitBtn.textContent = "Creando...";

    try {
      await userService.createUser({ full_name: fullName, email, role, password });
      Toast.success(`Usuario "${fullName}" creado exitosamente.`);
      closeModal();
      onSuccess();
    } catch (err: any) {
      Toast.error(err.message || "Error al crear usuario.");
    } finally {
      submitBtn.disabled = false;
      submitBtn.textContent = "Crear Usuario";
    }
  });
}
