import { authStore } from "../store/authStore";
import { authService } from "../services/authService";

export function renderNavbar(): string {
  const user = authStore.getUser();
  const userName = user?.fullName || user?.email || "Usuario";
  const userRole = user?.role || "CONSULTOR";

  return `
    <header class="navbar" style="
      height: var(--header-height);
      background-color: var(--bg-header);
      border-bottom: 1px solid var(--border-subtle);
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 0 1.75rem;
      position: sticky;
      top: 0;
      z-index: 50;
    ">
      <div style="display: flex; align-items: center; gap: 0.75rem;">
        <span style="
          display: inline-flex;
          align-items: center;
          gap: 0.5rem;
          font-size: 0.85rem;
          font-weight: 700;
          letter-spacing: 0.05em;
          color: #38BDF8;
          text-transform: uppercase;
        ">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
            <polyline points="14 2 14 8 20 8"/>
            <line x1="16" y1="13" x2="8" y2="13"/>
            <line x1="16" y1="17" x2="8" y2="17"/>
            <polyline points="10 9 9 9 8 9"/>
          </svg>
          Plataforma de Gestión de Hojas de Vida
        </span>
        <span style="font-size: 0.75rem; color: var(--text-muted); padding-left: 0.5rem; border-left: 1px solid var(--border-subtle);">
          Gobierno de Colombia
        </span>
      </div>

      <div style="display: flex; align-items: center; gap: 1rem;">
        <div style="display: flex; align-items: center; gap: 0.6rem; padding: 0.35rem 0.75rem; background: var(--bg-surface); border: 1px solid var(--border-subtle); border-radius: var(--radius-full);">
          <div style="width: 26px; height: 26px; border-radius: 50%; background: #0284C7; display: flex; align-items: center; justify-content: center; font-size: 0.75rem; font-weight: 700; color: #FFF;">
            ${userName.charAt(0).toUpperCase()}
          </div>
          <div style="display: flex; flex-direction: column;">
            <span style="font-size: 0.8rem; font-weight: 600; color: var(--text-primary); line-height: 1;">${userName}</span>
            <span style="font-size: 0.7rem; color: var(--text-muted); text-transform: uppercase; font-weight: 600; margin-top: 2px;">${userRole}</span>
          </div>
        </div>

        <button id="btn-logout" class="btn btn-outline btn-sm" title="Cerrar sesión" style="color: #F87171;">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
            <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/>
            <polyline points="16 17 21 12 16 7"/>
            <line x1="21" y1="12" x2="9" y2="12"/>
          </svg>
          Salir
        </button>
      </div>
    </header>
  `;
}

export function initNavbarEvents(): void {
  const logoutBtn = document.getElementById("btn-logout");
  logoutBtn?.addEventListener("click", async () => {
    await authService.logout();
  });
}
