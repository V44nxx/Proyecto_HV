import { documentService, DocumentItem } from "../services/documentService";
import { renderStatusBadge, renderFormatBadge } from "../components/StatusBadge";
import { renderPagination } from "../components/Pagination";
import { Toast } from "../components/Toast";

export async function renderDocumentsPage(container: HTMLElement): Promise<void> {
  container.innerHTML = `
    <div class="page-container" style="max-width: 1400px; margin: 0 auto; padding: 1.5rem;">
      <!-- Header -->
      <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 2rem; flex-wrap: wrap; gap: 1rem;">
        <div>
          <div style="font-size: 0.8rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.08em; color: #38BDF8; margin-bottom: 0.35rem;">
            Repositorio Documental
          </div>
          <h1 style="font-size: 1.75rem; font-weight: 700; color: var(--text-primary); margin: 0;">
            Gestión de Hojas de Vida
          </h1>
          <p style="font-size: 0.9rem; color: var(--text-secondary); margin-top: 0.25rem;">
            Cargue, clasifique y audite documentos en formato DAFP o ATS con trazabilidad visual.
          </p>
        </div>
      </div>

      <!-- Drag & Drop Upload Zone -->
      <div class="card" style="margin-bottom: 2rem; padding: 2rem; text-align: center; border: 2px dashed #334155; background: rgba(15, 23, 42, 0.6); transition: all var(--transition-fast);" id="drop-zone">
        <input type="file" id="file-input" accept="application/pdf" style="display: none;" />
        <div style="max-width: 480px; margin: 0 auto;">
          <div style="
            width: 52px;
            height: 52px;
            margin: 0 auto 1rem;
            border-radius: 50%;
            background: rgba(2, 132, 199, 0.15);
            display: flex;
            align-items: center;
            justify-content: center;
            color: #38BDF8;
          ">
            <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
              <polyline points="17 8 12 3 7 8"/>
              <line x1="12" y1="3" x2="12" y2="15"/>
            </svg>
          </div>
          <h3 style="font-size: 1.1rem; font-weight: 600; color: var(--text-primary); margin-bottom: 0.5rem;">
            Arrastre aquí su archivo PDF o haga clic para seleccionar
          </h3>
          <p style="font-size: 0.85rem; color: var(--text-muted); margin-bottom: 1.25rem;">
            Formatos admitidos: <strong>PDF nativo o escaneado</strong> (Formato Único de Función Pública o Hojas de Vida Estándar ATS). Tamaño máximo: 25 MB.
          </p>
          <button id="btn-browse-file" class="btn btn-primary btn-sm">
            Examinar archivos locales
          </button>
        </div>

        <!-- Upload Progress Indicator (Hidden by default) -->
        <div id="upload-progress-box" style="display: none; margin-top: 1.5rem; max-width: 440px; margin-left: auto; margin-right: auto;">
          <div style="display: flex; justify-content: space-between; font-size: 0.825rem; margin-bottom: 0.4rem;">
            <span id="upload-filename" style="color: var(--text-primary); font-weight: 600;">archivo.pdf</span>
            <span id="upload-pct" style="color: #38BDF8; font-family: var(--font-mono);">0%</span>
          </div>
          <div style="width: 100%; height: 6px; background: #1E293B; border-radius: 3px; overflow: hidden;">
            <div id="upload-bar" style="width: 0%; height: 100%; background: #0284C7; transition: width 0.3s ease;"></div>
          </div>
          <div id="upload-status-text" style="font-size: 0.75rem; color: var(--text-muted); margin-top: 0.4rem;">Subiendo a la plataforma...</div>
        </div>
      </div>

      <!-- Filter Controls Toolbar -->
      <div class="card" style="padding: 1rem 1.25rem; margin-bottom: 1.5rem;">
        <div style="display: flex; gap: 1rem; align-items: center; flex-wrap: wrap;">
          <div style="flex: 1; min-width: 240px; position: relative;">
            <input 
              type="text" 
              id="filter-search" 
              class="form-control" 
              placeholder="Buscar por nombre de archivo..."
              style="width: 100%; padding: 0.5rem 0.75rem 0.5rem 2.25rem; font-size: 0.85rem; background: #0B1120; border: 1px solid var(--border-subtle); color: #FFF; border-radius: var(--radius-sm);"
            />
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="position: absolute; left: 0.75rem; top: 50%; transform: translateY(-50%); color: var(--text-muted); pointer-events: none;">
              <circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>
            </svg>
          </div>

          <div style="width: 180px;">
            <select id="filter-status" class="form-control" style="width: 100%; padding: 0.5rem 0.75rem; font-size: 0.85rem; background: #0B1120; border: 1px solid var(--border-subtle); color: #FFF; border-radius: var(--radius-sm);">
              <option value="">Todos los Estados</option>
              <option value="UPLOADED">Subido</option>
              <option value="PROCESSING">Procesando</option>
              <option value="REVIEW_REQUIRED">En Revisión</option>
              <option value="COMPLETED">Completado</option>
              <option value="FAILED">Con Error</option>
            </select>
          </div>

          <div style="width: 180px;">
            <select id="filter-type" class="form-control" style="width: 100%; padding: 0.5rem 0.75rem; font-size: 0.85rem; background: #0B1120; border: 1px solid var(--border-subtle); color: #FFF; border-radius: var(--radius-sm);">
              <option value="">Todos los Formatos</option>
              <option value="FORMATO_UNICO">Formato Único (DAFP)</option>
              <option value="ATS">Estándar (ATS)</option>
            </select>
          </div>

          <button id="btn-apply-filters" class="btn btn-outline btn-sm">
            Filtrar
          </button>
        </div>
      </div>

      <!-- Document Table Container -->
      <div class="card" style="overflow: hidden; margin-bottom: 1.5rem;">
        <div style="overflow-x: auto;">
          <table style="width: 100%; border-collapse: collapse; font-size: 0.875rem;">
            <thead>
              <tr style="background: var(--bg-surface-elevated); color: var(--text-muted); font-size: 0.75rem; text-transform: uppercase;">
                <th style="padding: 0.75rem 1.25rem; text-align: left;">Nombre del Documento</th>
                <th style="padding: 0.75rem 1rem; text-align: left;">Formato</th>
                <th style="padding: 0.75rem 1rem; text-align: center;">Páginas</th>
                <th style="padding: 0.75rem 1rem; text-align: center;">Tamaño</th>
                <th style="padding: 0.75rem 1rem; text-align: left;">Estado</th>
                <th style="padding: 0.75rem 1rem; text-align: left;">Fecha</th>
                <th style="padding: 0.75rem 1.25rem; text-align: right;">Acciones</th>
              </tr>
            </thead>
            <tbody id="documents-table-body">
              <tr>
                <td colspan="7" style="text-align: center; padding: 3rem; color: var(--text-muted);">
                  <div class="spinner" style="margin-right: 0.5rem;"></div> Cargando listado de documentos...
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- Pagination Container -->
      <div id="documents-pagination"></div>
    </div>
  `;

  let currentPage = 1;
  const pageSize = 10;

  // Event Listeners for Filters
  const btnApply = container.querySelector("#btn-apply-filters");
  btnApply?.addEventListener("click", () => {
    currentPage = 1;
    loadDocuments(container, currentPage, pageSize);
  });

  const searchInput = container.querySelector("#filter-search") as HTMLInputElement;
  searchInput?.addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
      currentPage = 1;
      loadDocuments(container, currentPage, pageSize);
    }
  });

  // Setup Upload Zone
  setupUploadZone(container, () => {
    loadDocuments(container, currentPage, pageSize);
  });

  // Initial Data Fetch
  await loadDocuments(container, currentPage, pageSize);
}

function formatBytes(bytes: number): string {
  if (!bytes || bytes === 0) return "0 B";
  const k = 1024;
  const sizes = ["B", "KB", "MB", "GB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + " " + sizes[i];
}

async function loadDocuments(container: HTMLElement, page: number, pageSize: number): Promise<void> {
  const tbody = container.querySelector("#documents-table-body");
  if (!tbody) return;

  const searchInput = container.querySelector("#filter-search") as HTMLInputElement;
  const statusSelect = container.querySelector("#filter-status") as HTMLSelectElement;
  const typeSelect = container.querySelector("#filter-type") as HTMLSelectElement;

  try {
    const res = await documentService.list({
      page,
      page_size: pageSize,
      search: searchInput?.value.trim() || undefined,
      status: statusSelect?.value || undefined,
      document_type: typeSelect?.value || undefined,
    });

    if (!res.items || res.items.length === 0) {
      tbody.innerHTML = `
        <tr>
          <td colspan="7" style="text-align: center; padding: 3rem; color: var(--text-muted);">
            No se encontraron hojas de vida registradas con los filtros seleccionados.
          </td>
        </tr>
      `;
      renderPagination("documents-pagination", 1, 0, 0, () => {});
      return;
    }

    tbody.innerHTML = res.items.map((doc: DocumentItem) => `
      <tr style="border-bottom: 1px solid var(--border-subtle); transition: background var(--transition-fast);">
        <td style="padding: 0.85rem 1.25rem;">
          <div style="font-weight: 600; color: var(--text-primary); display: flex; align-items: center; gap: 0.5rem;">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#38BDF8" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
            <a href="#/documents/${doc.id}" style="color: #38BDF8; text-decoration: none;">
              ${doc.original_filename || doc.filename}
            </a>
          </div>
          <div style="font-size: 0.725rem; color: var(--text-muted); font-family: var(--font-mono); margin-top: 2px;">
            ID: ${doc.id.substring(0, 13)}...
          </div>
        </td>
        <td style="padding: 0.85rem 1rem;">
          ${renderFormatBadge(doc.document_type)}
        </td>
        <td style="padding: 0.85rem 1rem; text-align: center; font-family: var(--font-mono); font-size: 0.85rem;">
          ${doc.page_count || 1}
        </td>
        <td style="padding: 0.85rem 1rem; text-align: center; font-family: var(--font-mono); font-size: 0.825rem; color: var(--text-secondary);">
          ${formatBytes(doc.file_size_bytes)}
        </td>
        <td style="padding: 0.85rem 1rem;">
          ${renderStatusBadge(doc.status)}
        </td>
        <td style="padding: 0.85rem 1rem; font-size: 0.8rem; color: var(--text-muted);">
          ${new Date(doc.created_at).toLocaleDateString("es-CO", { year: "numeric", month: "short", day: "numeric" })}
        </td>
        <td style="padding: 0.85rem 1.25rem; text-align: right;">
          <div style="display: flex; gap: 0.4rem; justify-content: flex-end;">
            <a href="#/documents/${doc.id}" class="btn btn-outline btn-sm" title="Ver detalle y trazabilidad">
              Ver
            </a>
            <button class="btn btn-outline btn-sm btn-delete-doc" data-id="${doc.id}" data-name="${doc.original_filename || doc.filename}" style="color: #F87171;" title="Eliminar">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>
            </button>
          </div>
        </td>
      </tr>
    `).join("");

    // Setup Delete Buttons
    tbody.querySelectorAll(".btn-delete-doc").forEach((btn) => {
      btn.addEventListener("click", async (e) => {
        const target = e.currentTarget as HTMLElement;
        const docId = target.dataset.id;
        const docName = target.dataset.name;
        if (!docId) return;

        if (confirm(`¿Está seguro de eliminar permanentemente la hoja de vida "${docName}"?`)) {
          try {
            await documentService.delete(docId);
            Toast.success("Hoja de vida eliminada");
            loadDocuments(container, page, pageSize);
          } catch (err: any) {
            Toast.error(err.message || "Error al eliminar el documento");
          }
        }
      });
    });

    // Render Pagination
    renderPagination(
      "documents-pagination",
      res.page,
      res.total_pages,
      res.total,
      (newPage) => loadDocuments(container, newPage, pageSize)
    );
  } catch (err: any) {
    tbody.innerHTML = `
      <tr>
        <td colspan="7" style="text-align: center; padding: 2rem; color: var(--color-danger);">
          Error al cargar los documentos: ${err.message || "Fallo en conexión"}
        </td>
      </tr>
    `;
    Toast.error("Error al obtener listado de documentos");
  }
}

function setupUploadZone(container: HTMLElement, onUploadSuccess: () => void): void {
  const dropZone = container.querySelector("#drop-zone") as HTMLElement;
  const fileInput = container.querySelector("#file-input") as HTMLInputElement;
  const browseBtn = container.querySelector("#btn-browse-file") as HTMLButtonElement;
  const progressBox = container.querySelector("#upload-progress-box") as HTMLElement;
  const filenameEl = container.querySelector("#upload-filename") as HTMLElement;
  const pctEl = container.querySelector("#upload-pct") as HTMLElement;
  const barEl = container.querySelector("#upload-bar") as HTMLElement;
  const statusText = container.querySelector("#upload-status-text") as HTMLElement;

  browseBtn?.addEventListener("click", () => {
    fileInput?.click();
  });

  fileInput?.addEventListener("change", () => {
    if (fileInput.files && fileInput.files[0]) {
      handleFileUpload(fileInput.files[0]);
    }
  });

  // Drag and drop events
  dropZone?.addEventListener("dragover", (e) => {
    e.preventDefault();
    dropZone.style.borderColor = "#38BDF8";
    dropZone.style.background = "rgba(2, 132, 199, 0.1)";
  });

  dropZone?.addEventListener("dragleave", () => {
    dropZone.style.borderColor = "#334155";
    dropZone.style.background = "rgba(15, 23, 42, 0.6)";
  });

  dropZone?.addEventListener("drop", (e) => {
    e.preventDefault();
    dropZone.style.borderColor = "#334155";
    dropZone.style.background = "rgba(15, 23, 42, 0.6)";
    if (e.dataTransfer && e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFileUpload(e.dataTransfer.files[0]);
    }
  });

  async function handleFileUpload(file: File): Promise<void> {
    if (!file.name.toLowerCase().endsWith(".pdf")) {
      Toast.error("Únicamente se admiten archivos en formato PDF.");
      return;
    }

    if (file.size > 25 * 1024 * 1024) {
      Toast.error("El archivo supera el límite máximo permitido de 25 MB.");
      return;
    }

    progressBox.style.display = "block";
    filenameEl.textContent = file.name;
    pctEl.textContent = "45%";
    barEl.style.width = "45%";
    statusText.textContent = "Enviando documento a la API segura...";

    try {
      const uploadRes = await documentService.upload(file);
      pctEl.textContent = "100%";
      barEl.style.width = "100%";
      statusText.textContent = "Documento recibido y encolado para extracción.";
      Toast.success(`Documento "${file.name}" cargado exitosamente.`);

      setTimeout(() => {
        progressBox.style.display = "none";
        barEl.style.width = "0%";
        fileInput.value = "";
        onUploadSuccess();
        // Redirect to detail page for immediate review
        if (uploadRes.document?.id) {
          window.location.hash = `#/documents/${uploadRes.document.id}`;
        }
      }, 800);
    } catch (err: any) {
      statusText.textContent = "Error durante la subida.";
      barEl.style.background = "var(--color-danger)";
      Toast.error(err.message || "Error al subir el documento.");
    }
  }
}
