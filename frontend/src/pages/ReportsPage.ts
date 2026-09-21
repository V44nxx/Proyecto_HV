import { reportService, ReportCatalogItem, ReportPreviewResponse } from "../services/reportService";
import { Toast } from "../components/Toast";

export async function renderReportsPage(container: HTMLElement): Promise<void> {
  container.innerHTML = `
    <div class="page-container" style="max-width: 1400px; margin: 0 auto; padding: 1.5rem;">
      <!-- Header -->
      <div style="margin-bottom: 2rem;">
        <div style="font-size: 0.8rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.08em; color: #38BDF8; margin-bottom: 0.35rem;">
          Centro de Inteligencia y Analítica
        </div>
        <h1 style="font-size: 1.75rem; font-weight: 700; color: var(--text-primary); margin: 0;">
          Generación y Exportación de Reportes
        </h1>
        <p style="font-size: 0.9rem; color: var(--text-secondary); margin-top: 0.25rem;">
          Genere informes institucionales con previsualización en vivo y descarga en formatos Excel (.xlsx) y PDF (.pdf).
        </p>
      </div>

      <!-- Report Configuration Card -->
      <div class="card" style="padding: 1.5rem; margin-bottom: 1.5rem;">
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1.5rem; margin-bottom: 1.5rem;">
          <!-- Report Type Selector -->
          <div>
            <label class="form-label" style="display: block; font-size: 0.85rem; font-weight: 600; color: var(--text-secondary); margin-bottom: 0.4rem;">
              Tipo de Reporte Institucional
            </label>
            <select id="select-report-type" class="form-control" style="width: 100%; padding: 0.6rem 0.85rem; background: #0B1120; border: 1px solid var(--border-subtle); color: #FFF; border-radius: var(--radius-sm);">
              <option value="">Cargando catálogo de reportes...</option>
            </select>
            <div id="report-description" style="font-size: 0.8rem; color: var(--text-muted); margin-top: 0.5rem; line-height: 1.4;">
              Seleccione un reporte para visualizar su descripción y alcances.
            </div>
          </div>

          <!-- Date Filters -->
          <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1rem;">
            <div>
              <label class="form-label" style="display: block; font-size: 0.85rem; font-weight: 600; color: var(--text-secondary); margin-bottom: 0.4rem;">
                Fecha Desde
              </label>
              <input type="date" id="filter-date-from" class="form-control" style="width: 100%; padding: 0.6rem 0.85rem; background: #0B1120; border: 1px solid var(--border-subtle); color: #FFF; border-radius: var(--radius-sm);" />
            </div>
            <div>
              <label class="form-label" style="display: block; font-size: 0.85rem; font-weight: 600; color: var(--text-secondary); margin-bottom: 0.4rem;">
                Fecha Hasta
              </label>
              <input type="date" id="filter-date-to" class="form-control" style="width: 100%; padding: 0.6rem 0.85rem; background: #0B1120; border: 1px solid var(--border-subtle); color: #FFF; border-radius: var(--radius-sm);" />
            </div>
          </div>
        </div>

        <!-- Action Buttons -->
        <div style="display: flex; justify-content: space-between; align-items: center; border-top: 1px solid var(--border-subtle); padding-top: 1.25rem; flex-wrap: wrap; gap: 0.75rem;">
          <button id="btn-preview-report" class="btn btn-primary" style="padding: 0.6rem 1.25rem;">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>
            Previsualizar Muestra (50 filas)
          </button>

          <div style="display: flex; gap: 0.75rem;">
            <button id="btn-export-excel" class="btn btn-outline" style="color: #34D399; border-color: rgba(52, 211, 153, 0.4);">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="8" y1="13" x2="16" y2="17"/><line x1="16" y1="13" x2="8" y2="17"/></svg>
              Descargar Excel (.xlsx)
            </button>
            <button id="btn-export-pdf" class="btn btn-outline" style="color: #F87171; border-color: rgba(248, 113, 113, 0.4);">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
              Descargar PDF (.pdf)
            </button>
          </div>
        </div>
      </div>

      <!-- Preview Table Container -->
      <div class="card" style="overflow: hidden;">
        <div style="padding: 1.25rem 1.5rem; border-bottom: 1px solid var(--border-subtle); display: flex; justify-content: space-between; align-items: center;">
          <h2 id="preview-title" style="font-size: 1.1rem; font-weight: 700; color: var(--text-primary); margin: 0;">
            Previsualización del Reporte
          </h2>
          <span id="preview-count" class="badge" style="background: rgba(2, 132, 199, 0.15); color: #38BDF8;">
            0 registros
          </span>
        </div>
        <div id="preview-table-wrapper" style="overflow-x: auto; max-height: 520px;">
          <div style="text-align: center; padding: 4rem 1rem; color: var(--text-muted); font-size: 0.85rem;">
            Seleccione un reporte y haga clic en "Previsualizar Muestra" para cargar datos.
          </div>
        </div>
      </div>
    </div>
  `;

  let catalog: ReportCatalogItem[] = [];

  try {
    catalog = await reportService.getAvailableReports();
    populateCatalog(container, catalog);
  } catch (err: any) {
    Toast.error("Error al cargar catálogo de reportes.");
  }

  // Setup Preview & Export Handlers
  setupReportActions(container);
}

function populateCatalog(container: HTMLElement, catalog: ReportCatalogItem[]): void {
  const select = container.querySelector("#select-report-type") as HTMLSelectElement;
  const descEl = container.querySelector("#report-description") as HTMLElement;
  if (!select) return;

  select.innerHTML = "";
  catalog.forEach((item) => {
    const opt = document.createElement("option");
    opt.value = item.report_type;
    opt.textContent = item.title;
    select.appendChild(opt);
  });

  const updateDesc = () => {
    const current = catalog.find((c) => c.report_type === select.value);
    if (current && descEl) {
      descEl.textContent = `${current.description} Formatos soportados: ${current.supported_formats.join(", ")}.`;
    }
  };

  select.addEventListener("change", updateDesc);
  updateDesc();
}

function setupReportActions(container: HTMLElement): void {
  const select = container.querySelector("#select-report-type") as HTMLSelectElement;
  const dateFrom = container.querySelector("#filter-date-from") as HTMLInputElement;
  const dateTo = container.querySelector("#filter-date-to") as HTMLInputElement;
  const btnPreview = container.querySelector("#btn-preview-report") as HTMLButtonElement;
  const btnExcel = container.querySelector("#btn-export-excel") as HTMLButtonElement;
  const btnPdf = container.querySelector("#btn-export-pdf") as HTMLButtonElement;
  const tableWrapper = container.querySelector("#preview-table-wrapper") as HTMLElement;
  const countBadge = container.querySelector("#preview-count") as HTMLElement;
  const previewTitle = container.querySelector("#preview-title") as HTMLElement;

  const getFilters = () => {
    const filters: Record<string, any> = {};
    if (dateFrom.value) filters.date_from = dateFrom.value;
    if (dateTo.value) filters.date_to = dateTo.value;
    return filters;
  };

  // Preview Button Handler
  btnPreview?.addEventListener("click", async () => {
    const reportType = select.value;
    if (!reportType) {
      Toast.error("Seleccione un tipo de reporte.");
      return;
    }

    tableWrapper.innerHTML = `
      <div style="display: flex; justify-content: center; padding: 4rem; color: var(--text-muted);">
        <div class="spinner" style="margin-right: 0.5rem;"></div> Generando vista previa...
      </div>
    `;

    try {
      const preview: ReportPreviewResponse = await reportService.getPreview(reportType, getFilters());
      previewTitle.textContent = preview.title || "Previsualización";
      countBadge.textContent = `${preview.total_records} registros encontrados`;

      if (!preview.rows || preview.rows.length === 0) {
        tableWrapper.innerHTML = `
          <div style="text-align: center; padding: 3rem; color: var(--text-muted);">
            No se encontraron registros para los filtros seleccionados.
          </div>
        `;
        return;
      }

      // Render Dynamic Columns & Rows Table
      const cols = preview.columns || Object.keys(preview.rows[0]).map((k) => ({ key: k, label: k, align: "left" }));

      tableWrapper.innerHTML = `
        <table style="width: 100%; border-collapse: collapse; font-size: 0.85rem;">
          <thead>
            <tr style="background: var(--bg-surface-elevated); color: var(--text-muted); font-size: 0.75rem; text-transform: uppercase; position: sticky; top: 0; z-index: 5;">
              ${cols.map((c) => `<th style="padding: 0.75rem 1rem; text-align: ${c.align || 'left'};">${c.label}</th>`).join("")}
            </tr>
          </thead>
          <tbody>
            ${preview.rows.map((row) => `
              <tr style="border-bottom: 1px solid var(--border-subtle); transition: background var(--transition-fast);">
                ${cols.map((c) => `
                  <td style="padding: 0.65rem 1rem; text-align: ${c.align || 'left'}; color: var(--text-primary);">
                    ${row[c.key] !== null && row[c.key] !== undefined ? row[c.key] : "—"}
                  </td>
                `).join("")}
              </tr>
            `).join("")}
          </tbody>
        </table>
      `;

      Toast.success("Previsualización actualizada.");
    } catch (err: any) {
      tableWrapper.innerHTML = `<div style="color: var(--color-danger); padding: 2rem; text-align: center;">${err.message || "Error al generar reporte."}</div>`;
      Toast.error("Error al previsualizar reporte.");
    }
  });

  // Export Excel Handler
  btnExcel?.addEventListener("click", async () => {
    const reportType = select.value;
    if (!reportType) return;

    btnExcel.disabled = true;
    Toast.info("Generando archivo Excel...");

    try {
      const blob = await reportService.exportReport(reportType, "EXCEL", getFilters());
      downloadFile(blob, `Reporte_${reportType}_${new Date().toISOString().split("T")[0]}.xlsx`);
      Toast.success("Reporte Excel descargado.");
    } catch (err: any) {
      Toast.error(err.message || "Error al exportar Excel.");
    } finally {
      btnExcel.disabled = false;
    }
  });

  // Export PDF Handler
  btnPdf?.addEventListener("click", async () => {
    const reportType = select.value;
    if (!reportType) return;

    btnPdf.disabled = true;
    Toast.info("Generando documento PDF institucional...");

    try {
      const blob = await reportService.exportReport(reportType, "PDF", getFilters());
      downloadFile(blob, `Reporte_${reportType}_${new Date().toISOString().split("T")[0]}.pdf`);
      Toast.success("Reporte PDF descargado.");
    } catch (err: any) {
      Toast.error(err.message || "Error al exportar PDF.");
    } finally {
      btnPdf.disabled = false;
    }
  });
}

function downloadFile(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}
