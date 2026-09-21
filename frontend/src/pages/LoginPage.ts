import { authService } from "../services/authService";
import { Toast } from "../components/Toast";

export function renderLoginPage(container: HTMLElement): void {
  container.innerHTML = `
    <div class="login-wrapper" style="
      min-height: 100vh;
      width: 100%;
      display: flex;
      align-items: center;
      justify-content: center;
      background: radial-gradient(circle at 50% 20%, #1E293B 0%, #0B1120 100%);
      padding: 1.5rem;
    ">
      <div class="card card-elevated" style="
        width: 100%;
        max-width: 440px;
        padding: 2.5rem 2rem;
        background: rgba(15, 23, 42, 0.95);
        backdrop-filter: blur(12px);
        border: 1px solid rgba(56, 189, 248, 0.15);
        box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.7);
      ">
        <!-- Institutional Header -->
        <div style="text-align: center; margin-bottom: 2rem;">
          <div style="
            display: inline-flex;
            align-items: center;
            justify-content: center;
            width: 52px;
            height: 52px;
            border-radius: 12px;
            background: linear-gradient(135deg, #1B365D 0%, #0284C7 100%);
            margin-bottom: 1rem;
            box-shadow: 0 8px 16px rgba(2, 132, 199, 0.3);
          ">
            <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#FFFFFF" stroke-width="2">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
              <polyline points="14 2 14 8 20 8"/>
              <line x1="16" y1="13" x2="8" y2="13"/>
              <line x1="16" y1="17" x2="8" y2="17"/>
              <polyline points="10 9 9 9 8 9"/>
            </svg>
          </div>
          <div style="font-size: 0.75rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.1em; color: #38BDF8; margin-bottom: 0.35rem;">
            República de Colombia
          </div>
          <h1 style="font-size: 1.35rem; font-weight: 700; color: #F8FAFC; margin-bottom: 0.4rem;">
            Gestión de Hojas de Vida
          </h1>
          <p style="font-size: 0.85rem; color: var(--text-secondary); line-height: 1.4;">
            Sistema Institucional de Inteligencia Documental DAFP y ATS
          </p>
        </div>

        <!-- Login Form -->
        <form id="login-form">
          <div class="form-group" style="margin-bottom: 1.25rem;">
            <label class="form-label" for="login-username" style="display: block; margin-bottom: 0.4rem; font-size: 0.825rem; font-weight: 600; color: var(--text-secondary);">
              Correo Electrónico Institucional
            </label>
            <input 
              id="login-username" 
              type="email" 
              class="form-control" 
              required 
              placeholder="ejemplo@funcionpublica.gov.co" 
              value="admin@proyecto-hv.local"
              style="width: 100%; padding: 0.7rem 0.85rem; background: #0B1120; border: 1px solid var(--border-subtle); color: #FFF; border-radius: var(--radius-sm);"
            />
          </div>

          <div class="form-group" style="margin-bottom: 1.5rem;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.4rem;">
              <label class="form-label" for="login-password" style="font-size: 0.825rem; font-weight: 600; color: var(--text-secondary);">
                Contraseña
              </label>
            </div>
            <input 
              id="login-password" 
              type="password" 
              class="form-control" 
              required 
              placeholder="••••••••••••" 
              value="Admin_Dev_2024!"
              style="width: 100%; padding: 0.7rem 0.85rem; background: #0B1120; border: 1px solid var(--border-subtle); color: #FFF; border-radius: var(--radius-sm);"
            />
          </div>

          <div id="login-error" style="display: none; padding: 0.75rem; border-radius: var(--radius-sm); background: rgba(239, 68, 68, 0.15); border: 1px solid rgba(239, 68, 68, 0.3); color: #FCA5A5; font-size: 0.825rem; margin-bottom: 1.25rem;"></div>

          <button 
            type="submit" 
            id="login-submit-btn" 
            class="btn btn-primary" 
            style="width: 100%; padding: 0.75rem; font-weight: 600; font-size: 0.95rem; justify-content: center;"
          >
            Acceder a la Plataforma
          </button>
        </form>

        <div style="margin-top: 1.75rem; padding-top: 1.25rem; border-top: 1px solid var(--border-subtle); text-align: center; font-size: 0.75rem; color: var(--text-muted);">
          Acceso protegido por directivas OWASP y autenticación RBAC basada en tokens JWT.
        </div>
      </div>
    </div>
  `;

  const form = container.querySelector("#login-form") as HTMLFormElement;
  const usernameInput = container.querySelector("#login-username") as HTMLInputElement;
  const passwordInput = container.querySelector("#login-password") as HTMLInputElement;
  const submitBtn = container.querySelector("#login-submit-btn") as HTMLButtonElement;
  const errorBox = container.querySelector("#login-error") as HTMLDivElement;

  form?.addEventListener("submit", async (e) => {
    e.preventDefault();
    errorBox.style.display = "none";
    submitBtn.disabled = true;
    submitBtn.innerHTML = `<div class="spinner" style="width: 16px; height: 16px; border-width: 2px;"></div> Ingresando...`;

    try {
      const user = await authService.login(usernameInput.value.trim(), passwordInput.value);
      Toast.success(`Bienvenido(a), ${user.fullName}`);
      window.location.hash = "#/dashboard";
    } catch (err: any) {
      errorBox.textContent = err.message || "Credenciales de acceso inválidas o usuario inactivo.";
      errorBox.style.display = "block";
      Toast.error("Error al iniciar sesión");
    } finally {
      submitBtn.disabled = false;
      submitBtn.innerHTML = `Acceder a la Plataforma`;
    }
  });
}
