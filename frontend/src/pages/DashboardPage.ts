import { dashboardService, DashboardOverview } from "../services/dashboardService";
import { renderStatusBadge, renderFormatBadge } from "../components/StatusBadge";
import { Toast } from "../components/Toast";

export async function renderDashboardPage(container: HTMLElement): Promise<void> {
  container.innerHTML = `
    <div class="page-container" style="max-width: 1400px; margin: 0 auto; padding: 1.5rem;">
      <!-- Page Header -->
      <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 2rem; flex-wrap: wrap; gap: 1rem;">
        <div>
          <div style="font-size: 0.8rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.08em; color: #38BDF8; margin-bottom: 0.35rem;">
            Panel de Control Ejecutivo
          </div>
          <h1 style="font-size: 1.75rem; font-weight: 700; color: var(--text-primary); margin: 0;">
            Estado de Inteligencia Documental
          </h1>
          <p style="font-size: 0.9rem; color: var(--text-secondary); margin-top: 0.25rem;">
            Visión global del procesamiento de hojas de vida, calidad de extracción y cola de revisión humana.
          </p>
        </div>
        <div style="display: flex; gap: 0.75rem;">
          <a href="#/documents" class="btn btn-primary btn-sm" style="display: inline-flex; align-items: center; gap: 0.5rem;">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 5v14M5 12h14"/></svg>
            Subir Documentos
          </a>
          <button id="btn-refresh-dashboard" class="btn btn-outline btn-sm" title="Actualizar métricas">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M23 4v6h-6"/><path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"/></svg>
            Actualizar
          </button>
        </div>
      </div>

      <!-- Dashboard Body Container -->
      <div id="dashboard-content">
        <div style="display: flex; justify-content: center; padding: 4rem; color: var(--text-muted);">
          <div class="spinner" style="margin-right: 0.75rem;"></div> Cargando indicadores y métricas consolidadas...
        </div>
      </div>
    </div>
  `;

  const refreshBtn = container.querySelector("#btn-refresh-dashboard");
  refreshBtn?.addEventListener("click", () => {
    loadDashboardData(container);
  });

  await loadDashboardData(container);
}

async function loadDashboardData(container: HTMLElement): Promise<void> {
  const contentEl = container.querySelector("#dashboard-content");
  if (!contentEl) return;

  try {
    const data: DashboardOverview = await dashboardService.getOverview();
    renderDashboardOverview(contentEl, data);
  } catch (err: any) {
    contentEl.innerHTML = `
      <div class="card" style="padding: 2rem; text-align: center; border-color: rgba(239, 68, 68, 0.3);">
        <p style="color: var(--color-danger); font-weight: 600; margin-bottom: 0.5rem;">
          No se pudieron cargar las métricas del panel de control
        </p>
        <p style="color: var(--text-secondary); font-size: 0.85rem;">${err.message || "Error al conectar con el servicio."}</p>
        <button id="btn-retry-dashboard" class="btn btn-outline btn-sm" style="margin-top: 1rem;">Reintentar</button>
      </div>
    `;
    container.querySelector("#btn-retry-dashboard")?.addEventListener("click", () => loadDashboardData(container));
    Toast.error("Error al cargar el panel de control");
  }
}

function renderDashboardOverview(container: Element, data: DashboardOverview): void {
  const kpis = data.kpis || {
    total_documents: 0,
    total_persons: 0,
    processed_documents: 0,
    documents_requiring_review: 0,
    extraction_success_rate: 0,
  };

  const byFormat = data.distributions?.by_format || [];
  const topProfessions = data.distributions?.top_professions || [];
  const pendingReviews = data.pending_reviews || [];
  const recentActivity = data.recent_activity || [];

  // Format distributions HTML
  const formatRowsHtml = byFormat.length > 0
    ? byFormat.map(item => `
        <div style="margin-bottom: 1rem;">
          <div style="display: flex; justify-content: space-between; font-size: 0.85rem; margin-bottom: 0.35rem;">
            <span style="font-weight: 600; color: var(--text-primary);">${item.label}</span>
            <span style="color: var(--text-secondary); font-family: var(--font-mono);">${item.count} (${item.percentage}%)</span>
          </div>
          <div style="width: 100%; height: 8px; background: #1E293B; border-radius: 4px; overflow: hidden;">
            <div style="width: ${Math.min(100, item.percentage)}%; height: 100%; background: ${item.label.includes("Único") ? "#0284C7" : "#38BDF8"}; border-radius: 4px;"></div>
          </div>
        </div>
      `).join("")
    : `<div style="color: var(--text-muted); font-size: 0.85rem; padding: 1rem 0;">No hay datos de formatos aún.</div>`;

  // Top professions HTML
  const professionsHtml = topProfessions.length > 0
    ? topProfessions.map((prof, idx) => `
        <div style="display: flex; align-items: center; justify-content: space-between; padding: 0.5rem 0; border-bottom: 1px solid var(--border-subtle); font-size: 0.85rem;">
          <div style="display: flex; align-items: center; gap: 0.6rem;">
            <span style="font-size: 0.75rem; font-weight: 700; color: var(--text-muted); width: 18px;">#${idx + 1}</span>
            <span style="color: var(--text-primary); font-weight: 500;">${prof.label}</span>
          </div>
          <span class="badge" style="background: rgba(2, 132, 199, 0.15); color: #38BDF8; font-weight: 600;">
            ${prof.count}
          </span>
        </div>
      `).join("")
    : `<div style="color: var(--text-muted); font-size: 0.85rem; padding: 1rem 0;">Sin registros profesionales aún.</div>`;

  // Pending reviews HTML
  const pendingRowsHtml = pendingReviews.length > 0
    ? pendingReviews.slice(0, 5).map(item => `
        <tr style="border-bottom: 1px solid var(--border-subtle);">
          <td style="padding: 0.75rem 1rem; font-weight: 500;">
            <a href="#/documents/${item.document_id}" style="color: #38BDF8; text-decoration: none;">
              ${item.filename}
            </a>
          </td>
          <td style="padding: 0.75rem 1rem;">
            ${renderFormatBadge(item.document_type)}
          </td>
          <td style="padding: 0.75rem 1rem; text-align: center;">
            <span class="badge badge-warning">${item.pending_fields_count} campos</span>
          </td>
          <td style="padding: 0.75rem 1rem; text-align: center; font-family: var(--font-mono); font-size: 0.85rem;">
            ${Math.round(item.lowest_confidence * 100)}%
          </td>
          <td style="padding: 0.75rem 1rem; text-align: right;">
            <a href="#/documents/${item.document_id}" class="btn btn-outline btn-sm" style="font-size: 0.75rem; padding: 0.2rem 0.5rem;">
              Auditar
            </a>
          </td>
        </tr>
      `).join("")
    : `<tr><td colspan="5" style="text-align: center; padding: 1.5rem; color: var(--text-muted); font-size: 0.85rem;">No hay documentos en espera de revisión humana.</td></tr>`;

  // Recent activity HTML
  const activityRowsHtml = recentActivity.length > 0
    ? recentActivity.slice(0, 5).map(item => `
        <tr style="border-bottom: 1px solid var(--border-subtle);">
          <td style="padding: 0.75rem 1rem; font-weight: 500;">
            <a href="#/documents/${item.document_id}" style="color: var(--text-primary); text-decoration: none;">
              ${item.filename}
            </a>
            ${item.candidate_name ? `<div style="font-size: 0.75rem; color: var(--text-secondary);">${item.candidate_name}</div>` : ""}
          </td>
          <td style="padding: 0.75rem 1rem;">
            ${renderFormatBadge(item.document_type)}
          </td>
          <td style="padding: 0.75rem 1rem;">
            ${renderStatusBadge(item.status)}
          </td>
          <td style="padding: 0.75rem 1rem; font-size: 0.8rem; color: var(--text-muted); text-align: right;">
            ${new Date(item.updated_at).toLocaleString("es-CO", { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" })}
          </td>
        </tr>
      `).join("")
    : `<tr><td colspan="4" style="text-align: center; padding: 1.5rem; color: var(--text-muted); font-size: 0.85rem;">Sin actividad reciente.</td></tr>`;

  container.innerHTML = `
    <!-- Top KPI Grid -->
    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 1.25rem; margin-bottom: 2rem;">
      <div class="card metric-card">
        <div class="metric-label">Total Documentos</div>
        <div class="metric-value">${kpis.total_documents}</div>
        <div class="metric-subtext">Hojas de vida almacenadas</div>
      </div>

      <div class="card metric-card">
        <div class="metric-label">Candidatos Identificados</div>
        <div class="metric-value" style="color: #38BDF8;">${kpis.total_persons}</div>
        <div class="metric-subtext">Personas en base de datos</div>
      </div>

      <div class="card metric-card">
        <div class="metric-label">Documentos Procesados</div>
        <div class="metric-value" style="color: var(--color-success);">${kpis.processed_documents}</div>
        <div class="metric-subtext">Completados exitosamente</div>
      </div>

      <div class="card metric-card">
        <div class="metric-label">En Revisión Humana</div>
        <div class="metric-value" style="color: var(--color-warning);">${kpis.documents_requiring_review}</div>
        <div class="metric-subtext">Requieren verificación</div>
      </div>

      <div class="card metric-card">
        <div class="metric-label">Tasa de Éxito</div>
        <div class="metric-value" style="color: #A78BFA;">${Math.round(kpis.extraction_success_rate || 0)}%</div>
        <div class="metric-subtext">Precisión global del pipeline</div>
      </div>
    </div>

    <!-- Analytics & Review Split Grid -->
    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1.5rem; margin-bottom: 2rem;">
      <!-- Distributions Card -->
      <div class="card" style="padding: 1.5rem;">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1.25rem;">
          <h2 style="font-size: 1.05rem; font-weight: 700; color: var(--text-primary); margin: 0;">
            Distribución por Formato
          </h2>
          <span style="font-size: 0.75rem; color: var(--text-muted);">DAFP vs ATS</span>
        </div>
        ${formatRowsHtml}
      </div>

      <!-- Top Professions Card -->
      <div class="card" style="padding: 1.5rem;">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1.25rem;">
          <h2 style="font-size: 1.05rem; font-weight: 700; color: var(--text-primary); margin: 0;">
            Profesiones Más Frecuentes
          </h2>
          <a href="#/search" style="font-size: 0.75rem; color: #38BDF8; text-decoration: none;">Ver todas &rarr;</a>
        </div>
        ${professionsHtml}
      </div>
    </div>

    <!-- Tables Grid -->
    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1.5rem;">
      <!-- Pending Reviews Card -->
      <div class="card" style="overflow: hidden;">
        <div style="padding: 1.25rem 1.5rem; border-bottom: 1px solid var(--border-subtle); display: flex; justify-content: space-between; align-items: center;">
          <h2 style="font-size: 1.05rem; font-weight: 700; color: var(--text-primary); margin: 0;">
            Cola de Revisión Humana (HITL)
          </h2>
          <a href="#/reviews" class="btn btn-outline btn-sm" style="font-size: 0.75rem; padding: 0.25rem 0.5rem;">
            Ver Cola Completa
          </a>
        </div>
        <div style="overflow-x: auto;">
          <table style="width: 100%; border-collapse: collapse; font-size: 0.85rem;">
            <thead>
              <tr style="background: var(--bg-surface-elevated); color: var(--text-muted); font-size: 0.75rem; text-transform: uppercase;">
                <th style="padding: 0.6rem 1rem; text-align: left;">Documento</th>
                <th style="padding: 0.6rem 1rem; text-align: left;">Formato</th>
                <th style="padding: 0.6rem 1rem; text-align: center;">Campos</th>
                <th style="padding: 0.6rem 1rem; text-align: center;">Confianza</th>
                <th style="padding: 0.6rem 1rem; text-align: right;">Acción</th>
              </tr>
            </thead>
            <tbody>
              ${pendingRowsHtml}
            </tbody>
          </table>
        </div>
      </div>

      <!-- Recent Activity Card -->
      <div class="card" style="overflow: hidden;">
        <div style="padding: 1.25rem 1.5rem; border-bottom: 1px solid var(--border-subtle); display: flex; justify-content: space-between; align-items: center;">
          <h2 style="font-size: 1.05rem; font-weight: 700; color: var(--text-primary); margin: 0;">
            Actividad de Procesamiento
          </h2>
          <a href="#/documents" class="btn btn-outline btn-sm" style="font-size: 0.75rem; padding: 0.25rem 0.5rem;">
            Todas las HV
          </a>
        </div>
        <div style="overflow-x: auto;">
          <table style="width: 100%; border-collapse: collapse; font-size: 0.85rem;">
            <thead>
              <tr style="background: var(--bg-surface-elevated); color: var(--text-muted); font-size: 0.75rem; text-transform: uppercase;">
                <th style="padding: 0.6rem 1rem; text-align: left;">Archivo</th>
                <th style="padding: 0.6rem 1rem; text-align: left;">Tipo</th>
                <th style="padding: 0.6rem 1rem; text-align: left;">Estado</th>
                <th style="padding: 0.6rem 1rem; text-align: right;">Fecha</th>
              </tr>
            </thead>
            <tbody>
              ${activityRowsHtml}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  `;
}
