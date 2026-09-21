import { dashboardService, PendingReviewItem } from "../services/dashboardService";
import { renderFormatBadge } from "../components/StatusBadge";
import { Toast } from "../components/Toast";

export async function renderReviewsPage(container: HTMLElement): Promise<void> {
  container.innerHTML = `
    <div class="page-container" style="max-width: 1400px; margin: 0 auto; padding: 1.5rem;">
      <!-- Header -->
      <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 2rem; flex-wrap: wrap; gap: 1rem;">
        <div>
          <div style="font-size: 0.8rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.08em; color: #F59E0B; margin-bottom: 0.35rem;">
            Supervisión Humana (Human-in-the-Loop)
          </div>
          <h1 style="font-size: 1.75rem; font-weight: 700; color: var(--text-primary); margin: 0;">
            Bandeja de Revisión y Auditoría
          </h1>
          <p style="font-size: 0.9rem; color: var(--text-secondary); margin-top: 0.25rem;">
            Verificación y corrección de extracciones con baja confianza o ambigüedad detectada por el modelo.
          </p>
        </div>

        <button id="btn-refresh-reviews" class="btn btn-outline btn-sm">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M23 4v6h-6"/><path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"/></svg>
          Actualizar Cola
        </button>
      </div>

      <!-- Institutional Instructions Callout -->
      <div class="card" style="padding: 1.25rem 1.5rem; margin-bottom: 1.5rem; background: rgba(245, 158, 11, 0.05); border: 1px solid rgba(245, 158, 11, 0.2);">
        <div style="display: flex; gap: 0.85rem; align-items: flex-start;">
          <div style="color: #F59E0B; margin-top: 2px;">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
          </div>
          <div style="font-size: 0.85rem; color: var(--text-secondary); line-height: 1.5;">
            <strong style="color: #F8FAFC;">Protocolo de Validación de Hojas de Vida:</strong>
            Los documentos listados a continuación contienen campos extraídos con un umbral de confianza inferior al 70% o formatos no homogéneos. Al hacer clic en <strong>Auditar Hoja de Vida</strong>, accederá a la vista dividida interactiva donde podrá contrastar cada campo contra la página original del PDF y aplicar correcciones vinculantes.
          </div>
        </div>
      </div>

      <!-- Pending Table Card -->
      <div class="card" style="overflow: hidden;">
        <div style="overflow-x: auto;">
          <table style="width: 100%; border-collapse: collapse; font-size: 0.875rem;">
            <thead>
              <tr style="background: var(--bg-surface-elevated); color: var(--text-muted); font-size: 0.75rem; text-transform: uppercase;">
                <th style="padding: 0.75rem 1.25rem; text-align: left;">Documento</th>
                <th style="padding: 0.75rem 1rem; text-align: left;">Formato Detectado</th>
                <th style="padding: 0.75rem 1rem; text-align: center;">Campos Pendientes</th>
                <th style="padding: 0.75rem 1rem; text-align: center;">Menor Confianza</th>
                <th style="padding: 0.75rem 1rem; text-align: left;">Fecha de Subida</th>
                <th style="padding: 0.75rem 1.25rem; text-align: right;">Acción</th>
              </tr>
            </thead>
            <tbody id="reviews-table-body">
              <tr>
                <td colspan="6" style="text-align: center; padding: 3rem; color: var(--text-muted);">
                  <div class="spinner" style="margin-right: 0.5rem;"></div> Consultando cola de revisión...
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  `;

  const refreshBtn = container.querySelector("#btn-refresh-reviews");
  refreshBtn?.addEventListener("click", () => loadPendingReviews(container));

  await loadPendingReviews(container);
}

async function loadPendingReviews(container: HTMLElement): Promise<void> {
  const tbody = container.querySelector("#reviews-table-body");
  if (!tbody) return;

  try {
    const items: PendingReviewItem[] = await dashboardService.getPendingReviews(50);

    if (!items || items.length === 0) {
      tbody.innerHTML = `
        <tr>
          <td colspan="6" style="text-align: center; padding: 3rem; color: var(--text-muted);">
            <div style="color: var(--color-success); font-weight: 600; margin-bottom: 0.4rem; display: flex; align-items: center; justify-content: center; gap: 0.5rem;">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="20 6 9 17 4 12"/></svg>
              Excelente: No hay documentos pendientes de revisión humana en este momento.
            </div>
            <div style="font-size: 0.8rem;">Todas las extracciones vigentes cumplen los estándares de confianza requeridos.</div>
          </td>
        </tr>
      `;
      return;
    }

    tbody.innerHTML = items.map((item) => `
      <tr style="border-bottom: 1px solid var(--border-subtle); transition: background var(--transition-fast);">
        <td style="padding: 0.85rem 1.25rem;">
          <div style="font-weight: 600; color: var(--text-primary); display: flex; align-items: center; gap: 0.5rem;">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#F59E0B" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/></svg>
            <a href="#/documents/${item.document_id}" style="color: #38BDF8; text-decoration: none;">
              ${item.filename}
            </a>
          </div>
          <div style="font-size: 0.725rem; color: var(--text-muted); font-family: var(--font-mono); margin-top: 2px;">
            ID: ${item.document_id.substring(0, 13)}...
          </div>
        </td>
        <td style="padding: 0.85rem 1rem;">
          ${renderFormatBadge(item.document_type)}
        </td>
        <td style="padding: 0.85rem 1rem; text-align: center;">
          <span class="badge badge-warning" style="font-weight: 600;">
            ${item.pending_fields_count} campos
          </span>
        </td>
        <td style="padding: 0.85rem 1rem; text-align: center; font-family: var(--font-mono); font-size: 0.85rem; color: ${item.lowest_confidence < 0.5 ? '#F87171' : '#FBBF24'};">
          ${Math.round(item.lowest_confidence * 100)}%
        </td>
        <td style="padding: 0.85rem 1rem; font-size: 0.8rem; color: var(--text-muted);">
          ${new Date(item.uploaded_at).toLocaleDateString("es-CO", { year: "numeric", month: "short", day: "numeric" })}
        </td>
        <td style="padding: 0.85rem 1.25rem; text-align: right;">
          <a href="#/documents/${item.document_id}" class="btn btn-primary btn-sm" style="font-size: 0.8rem; padding: 0.35rem 0.85rem;">
            Auditar Hoja de Vida
          </a>
        </td>
      </tr>
    `).join("");
  } catch (err: any) {
    tbody.innerHTML = `
      <tr>
        <td colspan="6" style="text-align: center; padding: 2rem; color: var(--color-danger);">
          Error al cargar cola de revisión: ${err.message || "Fallo de conexión"}
        </td>
      </tr>
    `;
    Toast.error("Error al obtener cola de revisión");
  }
}
