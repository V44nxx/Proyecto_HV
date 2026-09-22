import { documentService, CanonicalResumeData } from "../services/documentService";
import { reviewService, ReviewField } from "../services/reviewService";
import { PdfViewer } from "../components/PdfViewer";
import { renderStatusBadge, renderFormatBadge } from "../components/StatusBadge";
import { Toast } from "../components/Toast";

type LayoutMode = "wide-data" | "balanced" | "only-data" | "only-pdf";

export async function renderDocumentDetailPage(container: HTMLElement, documentId: string): Promise<void> {
  container.innerHTML = `
    <div class="doc-detail-wrapper" style="width: 100%; height: calc(100vh - var(--header-height)); display: flex; flex-direction: column; padding: 0.75rem 1.25rem; box-sizing: border-box; overflow: hidden; background: var(--bg-app);">
      <!-- Top Header & Actions Bar -->
      <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.75rem; flex-wrap: wrap; gap: 0.75rem; flex-shrink: 0; background: var(--bg-surface); padding: 0.65rem 1rem; border-radius: var(--radius-md); border: 1px solid var(--border-subtle);">
        <!-- Left: Navigation and Document Title -->
        <div style="display: flex; align-items: center; gap: 0.75rem; min-width: 0;">
          <a href="#/documents" class="btn btn-outline btn-sm" style="display: inline-flex; align-items: center; gap: 0.35rem; flex-shrink: 0;">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="15 18 9 12 15 6"/></svg>
            Volver
          </a>
          <div style="min-width: 0;">
            <div style="display: flex; align-items: center; gap: 0.5rem; flex-wrap: wrap;">
              <h1 id="doc-title" style="font-size: 1.15rem; font-weight: 700; color: var(--text-primary); margin: 0; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 480px;">
                Cargando documento...
              </h1>
              <span id="doc-format-badge"></span>
              <span id="doc-status-badge"></span>
            </div>
            <div id="doc-meta-info" style="font-size: 0.75rem; color: var(--text-muted); font-family: var(--font-mono); margin-top: 2px;">
              ID: ${documentId}
            </div>
          </div>
        </div>

        <!-- Center: Interactive View Layout Switcher (Prioritize Data vs PDF) -->
        <div style="display: flex; align-items: center; background: var(--bg-surface-elevated); padding: 3px; border-radius: var(--radius-sm); border: 1px solid var(--border-subtle); gap: 2px;">
          <button id="btn-layout-wide-data" class="layout-btn active" title="Priorizar Tabla de Datos (35% PDF / 65% Datos)">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="7" height="18" rx="1"/><rect x="12" y="3" width="9" height="18" rx="1"/></svg>
            <span>Priorizar Datos</span>
          </button>
          <button id="btn-layout-balanced" class="layout-btn" title="Vista Equitativa (50% PDF / 50% Datos)">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="8.5" height="18" rx="1"/><rect x="12.5" y="3" width="8.5" height="18" rx="1"/></svg>
            <span>50 / 50</span>
          </button>
          <button id="btn-layout-only-data" class="layout-btn" title="Maximizar Datos (Ocultar PDF temporalmente)">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="18" height="18" rx="1"/><line x1="9" y1="3" x2="9" y2="21"/></svg>
            <span>Solo Datos</span>
          </button>
          <button id="btn-layout-only-pdf" class="layout-btn" title="Maximizar Visor PDF">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="18" height="18" rx="1"/><path d="M14 3v18"/></svg>
            <span>Solo PDF</span>
          </button>
        </div>

        <!-- Right: Operations Action Buttons -->
        <div style="display: flex; gap: 0.4rem; align-items: center; flex-wrap: wrap;">
          <button id="btn-reclassify" class="btn btn-outline btn-sm" title="Re-ejecutar clasificador DAFP / ATS">
            Clasificar
          </button>
          <button id="btn-extract-dafp" class="btn btn-outline btn-sm" title="Extraer estructura Formato Único">
            Extraer DAFP
          </button>
          <button id="btn-extract-ats" class="btn btn-outline btn-sm" title="Extraer estructura ATS">
            Extraer ATS
          </button>
          <button id="btn-download-pdf" class="btn btn-outline btn-sm" title="Descargar copia del PDF original">
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
            PDF Original
          </button>
          <button id="btn-finalize-review" class="btn btn-primary btn-sm" style="background: #10B981; border-color: #059669;">
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="20 6 9 17 4 12"/></svg>
            Finalizar
          </button>
        </div>
      </div>

      <!-- Main Workspace: Split Grid with Adjustable Ratios -->
      <div id="workspace-grid" class="workspace-grid layout-wide-data" style="display: grid; gap: 1rem; flex: 1; min-height: 0; width: 100%; overflow: hidden;">
        <!-- Left Column: Interactive PDF Viewer -->
        <div id="pdf-viewer-column" style="height: 100%; min-height: 0; min-width: 0; display: flex; flex-direction: column;">
          <div id="pdf-viewer-container" style="height: 100%; min-height: 0; width: 100%;"></div>
        </div>

        <!-- Right Column: Structured Data Panel & Traceability Tabs -->
        <div id="data-panel-card" class="card" style="display: flex; flex-direction: column; height: 100%; min-height: 0; min-width: 0; overflow: hidden; background: var(--bg-surface); border: 1px solid var(--border-subtle); border-radius: var(--radius-md);">
          <!-- Tab Navigation Bar -->
          <div style="
            display: flex;
            align-items: center;
            border-bottom: 1px solid var(--border-subtle);
            background: var(--bg-surface-elevated);
            overflow-x: auto;
            flex-shrink: 0;
            padding: 0 0.5rem;
          ">
            <button class="tab-btn active" data-tab="tab-personal">
              <span>Datos Personales</span>
            </button>
            <button class="tab-btn" data-tab="tab-contact">
              <span>Contacto</span>
            </button>
            <button class="tab-btn" data-tab="tab-education">
              <span>Educación</span>
              <span id="badge-count-edu" class="tab-count-badge">0</span>
            </button>
            <button class="tab-btn" data-tab="tab-experience">
              <span>Experiencia</span>
              <span id="badge-count-exp" class="tab-count-badge">0</span>
            </button>
            <button class="tab-btn" data-tab="tab-languages">
              <span>Idiomas</span>
              <span id="badge-count-lang" class="tab-count-badge">0</span>
            </button>
            <button class="tab-btn" data-tab="tab-review">
              <span>Auditoría / HITL</span>
              <span id="badge-count-review" class="tab-count-badge">0</span>
            </button>
          </div>

          <!-- Traceability Banner -->
          <div style="
            padding: 0.45rem 1rem;
            background: rgba(2, 132, 199, 0.08);
            border-bottom: 1px solid rgba(2, 132, 199, 0.15);
            font-size: 0.775rem;
            color: #38BDF8;
            display: flex;
            align-items: center;
            justify-content: space-between;
            flex-shrink: 0;
          ">
            <span style="display: flex; align-items: center; gap: 0.45rem;">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg>
              Haga clic en cualquier fila o campo para saltar al origen exacto en el visor PDF.
            </span>
            <span id="extracted-fields-badge" class="badge" style="background: rgba(56, 189, 248, 0.2); color: #38BDF8; font-weight: 600;">
              0 campos estructurados
            </span>
          </div>

          <!-- Tab Content Scrollable Container -->
          <div id="tab-content-wrapper" style="flex: 1; overflow-y: auto; padding: 1.25rem; min-height: 0;">
            <!-- Tab: Personal Data -->
            <div id="tab-personal" class="tab-pane active">
              <!-- Hero Candidate Card -->
              <div id="personal-hero-card" style="margin-bottom: 1.25rem;"></div>
              <!-- Grid of Detailed Identity Fields -->
              <div id="personal-fields" style="display: grid; grid-template-columns: repeat(auto-fill, minmax(240px, 1fr)); gap: 0.85rem;"></div>
            </div>

            <!-- Tab: Contact Information -->
            <div id="tab-contact" class="tab-pane" style="display: none;">
              <div id="contact-fields" style="display: grid; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); gap: 0.85rem;"></div>
            </div>

            <!-- Tab: Education -->
            <div id="tab-education" class="tab-pane" style="display: none;">
              <div id="education-fields"></div>
            </div>

            <!-- Tab: Experience -->
            <div id="tab-experience" class="tab-pane" style="display: none;">
              <div id="experience-summary-box" style="margin-bottom: 1.25rem;"></div>
              <div id="experience-fields"></div>
            </div>

            <!-- Tab: Languages -->
            <div id="tab-languages" class="tab-pane" style="display: none;">
              <div id="languages-fields"></div>
            </div>

            <!-- Tab: Review & HITL Fields -->
            <div id="tab-review" class="tab-pane" style="display: none;">
              <div id="review-fields-container" style="display: flex; flex-direction: column; gap: 0.75rem;"></div>
            </div>
          </div>
        </div>
      </div>
    </div>
  `;

  // Inject Styles for Layout Switcher, Data Tables, and Responsive Cards
  const styleEl = document.createElement("style");
  styleEl.textContent = `
    /* Layout Sizing Modes */
    .workspace-grid.layout-wide-data {
      grid-template-columns: minmax(400px, 42%) minmax(480px, 58%) !important;
    }
    .workspace-grid.layout-balanced {
      grid-template-columns: minmax(360px, 50%) minmax(360px, 50%) !important;
    }
    .workspace-grid.layout-only-data {
      grid-template-columns: 1fr !important;
    }
    .workspace-grid.layout-only-data #pdf-viewer-column {
      display: none !important;
    }
    .workspace-grid.layout-only-pdf {
      grid-template-columns: 1fr !important;
    }
    .workspace-grid.layout-only-pdf #data-panel-card {
      display: none !important;
    }

    /* Layout Toggle Buttons */
    .layout-btn {
      display: inline-flex;
      align-items: center;
      gap: 0.35rem;
      padding: 0.28rem 0.55rem;
      border: none;
      background: transparent;
      color: var(--text-muted);
      font-size: 0.75rem;
      font-weight: 500;
      border-radius: 4px;
      cursor: pointer;
      transition: all var(--transition-fast);
      white-space: nowrap;
    }
    .layout-btn:hover {
      color: var(--text-primary);
      background: rgba(255, 255, 255, 0.05);
    }
    .layout-btn.active {
      color: #38BDF8;
      background: rgba(56, 189, 248, 0.12);
      font-weight: 600;
    }

    /* Tabs Styling */
    .tab-btn {
      display: inline-flex;
      align-items: center;
      gap: 0.4rem;
      padding: 0.75rem 1rem;
      background: transparent;
      border: none;
      border-bottom: 2px solid transparent;
      color: var(--text-secondary);
      font-size: 0.825rem;
      font-weight: 500;
      cursor: pointer;
      white-space: nowrap;
      transition: all var(--transition-fast);
    }
    .tab-btn:hover {
      color: var(--text-primary);
      background: rgba(255, 255, 255, 0.02);
    }
    .tab-btn.active {
      color: #38BDF8;
      border-bottom-color: #38BDF8;
      font-weight: 600;
      background: rgba(56, 189, 248, 0.05);
    }
    .tab-count-badge {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      padding: 0.1rem 0.4rem;
      font-size: 0.7rem;
      font-weight: 700;
      border-radius: 9999px;
      background: rgba(255, 255, 255, 0.08);
      color: var(--text-muted);
    }
    .tab-btn.active .tab-count-badge {
      background: rgba(56, 189, 248, 0.25);
      color: #38BDF8;
    }

    /* Traceable Interactive Cards & Rows */
    .traceable-card {
      cursor: pointer;
      padding: 0.75rem 0.95rem;
      background: var(--bg-surface-elevated);
      border: 1px solid var(--border-subtle);
      border-radius: var(--radius-sm);
      transition: all var(--transition-fast);
      display: flex;
      flex-direction: column;
      justify-content: space-between;
    }
    .traceable-card:hover {
      border-color: #38BDF8;
      background: rgba(56, 189, 248, 0.05);
      box-shadow: 0 4px 12px -2px rgba(0, 0, 0, 0.3);
      transform: translateY(-1px);
    }

    /* Data Table Styling for Education & Experience */
    .data-table-container {
      border: 1px solid var(--border-subtle);
      border-radius: var(--radius-sm);
      overflow: hidden;
      background: var(--bg-surface-elevated);
    }
    .data-table {
      width: 100%;
      border-collapse: collapse;
      font-size: 0.825rem;
      text-align: left;
    }
    .data-table th {
      background: #111B2E;
      color: var(--text-secondary);
      font-weight: 600;
      padding: 0.65rem 0.85rem;
      border-bottom: 1px solid var(--border-subtle);
      text-transform: uppercase;
      font-size: 0.7rem;
      letter-spacing: 0.5px;
    }
    .data-table td {
      padding: 0.75rem 0.85rem;
      border-bottom: 1px solid rgba(51, 65, 85, 0.6);
      color: var(--text-primary);
      vertical-align: top;
    }
    .data-table tr:last-child td {
      border-bottom: none;
    }
    .data-table tr.clickable-row {
      cursor: pointer;
      transition: background var(--transition-fast);
    }
    .data-table tr.clickable-row:hover td {
      background: rgba(56, 189, 248, 0.06);
    }
  `;
  container.appendChild(styleEl);

  // Initialize PDF Viewer instance
  const pdfContainer = container.querySelector("#pdf-viewer-container") as HTMLElement;
  const pdfViewer = new PdfViewer(pdfContainer);

  // Wire Layout Switcher Events
  setupLayoutSwitchers(container, pdfViewer);

  // Wire Tab Switching
  setupTabEvents(container);

  // Load Document, PDF Blob, and Structured Data
  await loadFullDocumentView(container, documentId, pdfViewer);
}

function setupLayoutSwitchers(container: HTMLElement, pdfViewer: PdfViewer): void {
  const grid = container.querySelector("#workspace-grid") as HTMLElement;
  const buttons = {
    "wide-data": container.querySelector("#btn-layout-wide-data"),
    "balanced": container.querySelector("#btn-layout-balanced"),
    "only-data": container.querySelector("#btn-layout-only-data"),
    "only-pdf": container.querySelector("#btn-layout-only-pdf"),
  };

  const setLayout = (mode: LayoutMode) => {
    Object.values(buttons).forEach((b) => b?.classList.remove("active"));
    grid.classList.remove("layout-wide-data", "layout-balanced", "layout-only-data", "layout-only-pdf");

    grid.classList.add(`layout-${mode}`);
    buttons[mode]?.classList.add("active");

    // Automatically re-fit PDF viewer on layout change
    setTimeout(() => {
      pdfViewer.fitToWidth();
    }, 250);
  };

  buttons["wide-data"]?.addEventListener("click", () => setLayout("wide-data"));
  buttons["balanced"]?.addEventListener("click", () => setLayout("balanced"));
  buttons["only-data"]?.addEventListener("click", () => setLayout("only-data"));
  buttons["only-pdf"]?.addEventListener("click", () => setLayout("only-pdf"));
}

function setupTabEvents(container: HTMLElement): void {
  const tabButtons = container.querySelectorAll(".tab-btn");
  const tabPanes = container.querySelectorAll(".tab-pane");

  tabButtons.forEach((btn) => {
    btn.addEventListener("click", () => {
      const targetTabId = (btn as HTMLElement).dataset.tab;
      if (!targetTabId) return;

      tabButtons.forEach((b) => b.classList.remove("active"));
      tabPanes.forEach((p) => {
        (p as HTMLElement).style.display = "none";
        p.classList.remove("active");
      });

      btn.classList.add("active");
      const targetPane = container.querySelector(`#${targetTabId}`) as HTMLElement;
      if (targetPane) {
        targetPane.style.display = "block";
        targetPane.classList.add("active");
      }
    });
  });
}

async function loadFullDocumentView(
  container: HTMLElement,
  documentId: string,
  pdfViewer: PdfViewer
): Promise<void> {
  try {
    // 1. Fetch document metadata
    const docRes = await documentService.getById(documentId);
    const doc = docRes.document || docRes;
    const latestJob = docRes.latest_job;
    updateDocHeader(container, doc, latestJob);

    // 2. Fetch original PDF binary stream
    documentService.downloadBlob(documentId).then((blob) => {
      pdfViewer.loadFromBlob(blob);
    }).catch((err) => {
      console.warn("Could not download PDF blob directly:", err);
    });

    // 3. Fetch canonical extraction data
    try {
      const canonicalData = await documentService.getCanonicalResume(documentId);
      renderCanonicalTabs(container, canonicalData, pdfViewer);
    } catch {
      renderEmptyCanonical(container);
    }

    // 4. Fetch HITL review fields
    loadReviewFields(container, documentId, pdfViewer);

    // 5. Wire action bar buttons
    wireActionButtons(container, documentId, pdfViewer);

  } catch (err: any) {
    Toast.error(err.message || "Error al cargar la hoja de vida.");
  }
}

function updateDocHeader(container: HTMLElement, doc: any, job?: any): void {
  const titleEl = container.querySelector("#doc-title");
  const formatEl = container.querySelector("#doc-format-badge");
  const statusEl = container.querySelector("#doc-status-badge");
  const metaEl = container.querySelector("#doc-meta-info");

  const status = job?.status || doc.status || "COMPLETED";
  const docType = doc.document_type || "UNKNOWN";

  if (titleEl) titleEl.textContent = doc.original_filename || doc.filename || "Hoja de Vida";
  if (formatEl) formatEl.innerHTML = renderFormatBadge(docType);
  if (statusEl) statusEl.innerHTML = renderStatusBadge(status);
  if (metaEl) {
    const dateStr = doc.created_at ? new Date(doc.created_at).toLocaleDateString("es-CO") : "Hoy";
    const checksum = (doc.checksum_sha256 || doc.sha256_checksum || "").substring(0, 16);
    metaEl.textContent = `Páginas: ${doc.page_count || 1} • Subido: ${dateStr}${checksum ? ` • SHA256: ${checksum}...` : ""}`;
  }
}

function renderCanonicalTabs(
  container: HTMLElement,
  data: CanonicalResumeData,
  pdfViewer: PdfViewer
): void {
  const badge = container.querySelector("#extracted-fields-badge");
  if (badge) {
    badge.textContent = `${data.extracted_fields_count || 0} campos estructurados`;
  }

  // Update Counters on Tabs
  const eduCountEl = container.querySelector("#badge-count-edu");
  if (eduCountEl) eduCountEl.textContent = (data.educations?.length || 0).toString();

  const expCountEl = container.querySelector("#badge-count-exp");
  if (expCountEl) expCountEl.textContent = (data.work_experiences?.length || 0).toString();

  const langCountEl = container.querySelector("#badge-count-lang");
  if (langCountEl) langCountEl.textContent = (data.languages?.length || 0).toString();

  // Update document title with candidate name and profession badge
  if (data.person) {
    const p = data.person;
    const titleEl = container.querySelector("#doc-title");
    if (titleEl) {
      const candidateName = `${p.first_name || ""} ${p.first_surname || ""}`.trim();
      const profName = p.profession || p.headline;
      if (candidateName) {
        titleEl.innerHTML = `<span>${candidateName}</span>${profName ? ` <span class="badge" style="background: rgba(56, 189, 248, 0.2); color: #38BDF8; font-size: 0.775rem; margin-left: 0.4rem; font-weight: 600;">${profName}</span>` : ""}`;
      }
    }
  }

  // 1. Personal Data Tab
  const heroEl = container.querySelector("#personal-hero-card");
  const personalEl = container.querySelector("#personal-fields");
  if (data.person) {
    const p = data.person;
    const fullName = `${p.first_name || ""} ${p.middle_name || ""} ${p.first_surname || ""} ${p.second_surname || ""}`.replace(/\s+/g, " ").trim();

    if (heroEl) {
      heroEl.innerHTML = `
        <div style="background: linear-gradient(135deg, rgba(27, 54, 93, 0.7) 0%, rgba(15, 23, 42, 0.9) 100%); border: 1px solid rgba(56, 189, 248, 0.3); border-radius: var(--radius-sm); padding: 1.1rem 1.25rem; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 1rem;">
          <div>
            <div style="font-size: 0.75rem; color: #38BDF8; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 0.25rem;">
              Candidato Identificado
            </div>
            <h2 style="font-size: 1.25rem; font-weight: 700; color: #FFF; margin: 0 0 0.4rem 0;">
              ${fullName || "Sin Nombre Registrado"}
            </h2>
            <div style="display: flex; gap: 0.5rem; flex-wrap: wrap; align-items: center;">
              <span class="badge" style="background: rgba(56, 189, 248, 0.2); color: #38BDF8; font-weight: 600; font-size: 0.8rem;">
                ${p.profession || p.headline || "Profesión no clasificada"}
              </span>
              <span class="badge" style="background: rgba(255, 255, 255, 0.08); color: var(--text-secondary); font-size: 0.8rem;">
                ${p.category || "Sector General"}
              </span>
            </div>
          </div>
          <div style="text-align: right; font-family: var(--font-mono); font-size: 0.85rem; color: var(--text-secondary);">
            <div style="color: #FFF; font-weight: 600; font-size: 0.95rem;">
              ${p.identification_type || "CC"}: ${p.identification_number || "No registrado"}
            </div>
            <div style="margin-top: 0.2rem; font-size: 0.8rem; color: var(--text-muted);">
              Tarjeta / Libreta: ${p.professional_card_number || p.military_card_number || "No registrada"}
            </div>
          </div>
        </div>
      `;
    }

    if (personalEl) {
      personalEl.innerHTML = `
        ${renderFieldCard("Profesión Principal", p.profession || p.headline || "No clasificada", 1, true, 2)}
        ${renderFieldCard("Categoría Profesional", p.category || "No registrada", 1, true, 2)}
        ${renderFieldCard("Documento de Identidad", `${p.identification_type || "CC"} ${p.identification_number || "No registrado"}`, 1)}
        ${renderFieldCard("Fecha de Nacimiento", p.birth_date || "No registrada", 1)}
        ${renderFieldCard("Nombres", `${p.first_name || ""} ${p.middle_name || ""}`.trim(), 1)}
        ${renderFieldCard("Apellidos", `${p.first_surname || ""} ${p.second_surname || ""}`.trim(), 1)}
        ${renderFieldCard("Tarjeta Profesional / Libreta", p.professional_card_number || p.military_card_number || "No registrada", 1)}
        ${renderFieldCard("Lugar de Nacimiento / Mun.", p.birth_municipality || p.birth_department || "No registrado", 1)}
        ${renderFieldCard("Nacionalidad", p.nationality || "Colombiana", 1)}
        ${renderFieldCard("Sexo", p.sex || "No especificado", 1)}
      `;
    }
  }

  // 2. Contact Tab
  const contactEl = container.querySelector("#contact-fields");
  if (contactEl && data.contact) {
    const c = data.contact;
    contactEl.innerHTML = `
      ${renderFieldCard("Dirección de Residencia", c.address || "No registrada", 1, false, 2)}
      ${renderFieldCard("Correo Electrónico", c.email || "No registrado", 1, true, 2)}
      ${renderFieldCard("Teléfono Celular", c.mobile_phone || "No registrado", 1)}
      ${renderFieldCard("Teléfono Fijo", c.telephone || "No registrado", 1)}
      ${renderFieldCard("Municipio / Ciudad", c.municipality || "No registrado", 1)}
      ${renderFieldCard("Departamento", c.department || "No registrado", 1)}
      ${renderFieldCard("País", c.country || "Colombia", 1)}
    `;
  }

  // 3. Education Tab (Full Structured Table)
  const eduEl = container.querySelector("#education-fields");
  if (eduEl) {
    if (data.educations && data.educations.length > 0) {
      eduEl.innerHTML = `
        <div class="data-table-container">
          <table class="data-table">
            <thead>
              <tr>
                <th style="width: 28%;">Título / Programa</th>
                <th style="width: 18%;">Nivel Académico</th>
                <th style="width: 26%;">Institución</th>
                <th style="width: 14%;">Año / Graduado</th>
                <th style="width: 14%; text-align: center;">Página Fuente</th>
              </tr>
            </thead>
            <tbody>
              ${data.educations.map((edu, idx) => {
                const pageNum = (edu as any).source_page || (idx > 1 ? 2 : 1);
                return `
                  <tr class="clickable-row traceable-row" data-page="${pageNum}">
                    <td>
                      <div style="font-weight: 600; color: #FFF; font-size: 0.875rem;">
                        ${edu.degree_title || "Título no especificado"}
                      </div>
                      ${edu.professional_card_number ? `
                        <div style="font-size: 0.75rem; color: #38BDF8; margin-top: 3px; font-family: var(--font-mono);">
                          Tarjeta: ${edu.professional_card_number}
                        </div>
                      ` : ""}
                    </td>
                    <td>
                      <span class="badge" style="background: rgba(56, 189, 248, 0.12); color: #38BDF8; font-weight: 500;">
                        ${edu.academic_level || "Superior"}
                      </span>
                    </td>
                    <td style="color: var(--text-secondary); line-height: 1.35;">
                      ${edu.institution || "Institución no especificada"}
                    </td>
                    <td>
                      <div style="font-weight: 600; color: #FFF;">
                        ${edu.graduation_date || (edu as any).completion_year || "—"}
                      </div>
                      <div style="font-size: 0.725rem; color: ${edu.is_graduated !== false ? 'var(--color-success)' : 'var(--text-muted)'};">
                        ${edu.is_graduated !== false ? "✓ Graduado" : "En curso"}
                      </div>
                    </td>
                    <td style="text-align: center;">
                      <span class="badge" style="background: rgba(2, 132, 199, 0.15); color: #38BDF8; font-size: 0.75rem;">
                        Pág. ${pageNum} &rarr;
                      </span>
                    </td>
                  </tr>
                `;
              }).join("")}
            </tbody>
          </table>
        </div>
      `;
    } else {
      eduEl.innerHTML = `<div style="color: var(--text-muted); padding: 2rem; text-align: center;">No se encontraron registros de educación formal.</div>`;
    }
  }

  // 4. Experience Tab (Full Structured Table & Metric Cards)
  const expEl = container.querySelector("#experience-fields");
  const expSummaryEl = container.querySelector("#experience-summary-box");

  if (expSummaryEl && data.experience_summary) {
    const s = data.experience_summary;
    expSummaryEl.innerHTML = `
      <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 0.75rem;">
        <div style="background: linear-gradient(135deg, rgba(16, 185, 129, 0.15) 0%, rgba(5, 150, 105, 0.05) 100%); border: 1px solid rgba(16, 185, 129, 0.3); border-radius: var(--radius-sm); padding: 0.85rem 1rem;">
          <div style="font-size: 0.725rem; font-weight: 600; color: #34D399; text-transform: uppercase;">Total Experiencia</div>
          <div style="font-size: 1.25rem; font-weight: 700; color: #FFF; margin-top: 0.2rem;">
            ${s.total_experience_display || `${s.total_experience_months || 0} meses`}
          </div>
        </div>
        <div style="background: rgba(56, 189, 248, 0.08); border: 1px solid rgba(56, 189, 248, 0.2); border-radius: var(--radius-sm); padding: 0.85rem 1rem;">
          <div style="font-size: 0.725rem; font-weight: 600; color: #38BDF8; text-transform: uppercase;">Sector Público</div>
          <div style="font-size: 1.15rem; font-weight: 700; color: #FFF; margin-top: 0.2rem;">
            ${s.public_experience_display || `${s.public_experience_months || 0} meses`}
          </div>
        </div>
        <div style="background: rgba(255, 255, 255, 0.04); border: 1px solid var(--border-subtle); border-radius: var(--radius-sm); padding: 0.85rem 1rem;">
          <div style="font-size: 0.725rem; font-weight: 600; color: var(--text-secondary); text-transform: uppercase;">Sector Privado</div>
          <div style="font-size: 1.15rem; font-weight: 700; color: #FFF; margin-top: 0.2rem;">
            ${s.private_experience_months ? `${s.private_experience_months} meses` : "—"}
          </div>
        </div>
      </div>
    `;
  }

  if (expEl) {
    if (data.work_experiences && data.work_experiences.length > 0) {
      expEl.innerHTML = `
        <div class="data-table-container">
          <table class="data-table">
            <thead>
              <tr>
                <th style="width: 25%;">Cargo Desempeñado</th>
                <th style="width: 30%;">Empresa / Entidad</th>
                <th style="width: 15%;">Sector</th>
                <th style="width: 18%;">Periodo / Duración</th>
                <th style="width: 12%; text-align: center;">Página</th>
              </tr>
            </thead>
            <tbody>
              ${data.work_experiences.map((exp, idx) => {
                const pageNum = (exp as any).source_page || (idx > 1 ? (idx > 4 ? 3 : 2) : 1);
                return `
                  <tr class="clickable-row traceable-row" data-page="${pageNum}">
                    <td>
                      <div style="font-weight: 600; color: #FFF; font-size: 0.875rem;">
                        ${exp.position || "Cargo no especificado"}
                      </div>
                      ${exp.responsibilities ? `
                        <div style="font-size: 0.775rem; color: var(--text-muted); margin-top: 0.25rem; line-height: 1.35; max-height: 50px; overflow: hidden; text-overflow: ellipsis;">
                          ${exp.responsibilities}
                        </div>
                      ` : ""}
                    </td>
                    <td>
                      <div style="font-weight: 500; color: var(--text-primary);">
                        ${exp.company_name}
                      </div>
                    </td>
                    <td>
                      <span class="badge" style="background: ${exp.is_public_sector ? 'rgba(56, 189, 248, 0.15)' : 'rgba(255, 255, 255, 0.08)'}; color: ${exp.is_public_sector ? '#38BDF8' : 'var(--text-secondary)'}; font-size: 0.725rem;">
                        ${exp.is_public_sector ? "Público" : "Privado / Indep."}
                      </span>
                    </td>
                    <td>
                      <div style="font-size: 0.8rem; color: #FFF; font-family: var(--font-mono);">
                        ${exp.start_date || "—"} &rarr; ${exp.is_current ? "Presente" : (exp.end_date || "—")}
                      </div>
                      ${exp.total_months ? `
                        <div style="font-size: 0.725rem; color: var(--text-muted); margin-top: 2px;">
                          ${exp.total_months} meses
                        </div>
                      ` : ""}
                    </td>
                    <td style="text-align: center;">
                      <span class="badge" style="background: rgba(2, 132, 199, 0.15); color: #38BDF8; font-size: 0.75rem;">
                        Pág. ${pageNum} &rarr;
                      </span>
                    </td>
                  </tr>
                `;
              }).join("")}
            </tbody>
          </table>
        </div>
      `;
    } else {
      expEl.innerHTML = `<div style="color: var(--text-muted); padding: 2rem; text-align: center;">No se encontraron registros de experiencia laboral.</div>`;
    }
  }

  // 5. Languages Tab
  const langEl = container.querySelector("#languages-fields");
  if (langEl) {
    if (data.languages && data.languages.length > 0) {
      langEl.innerHTML = `
        <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 1rem;">
          ${data.languages.map((l) => `
            <div class="traceable-card traceable-row" data-page="2">
              <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.75rem;">
                <span style="font-weight: 700; color: #FFF; font-size: 0.95rem;">${l.language}</span>
                <span class="badge" style="background: rgba(2, 132, 199, 0.15); color: #38BDF8; font-size: 0.725rem;">Pág. 2 &rarr;</span>
              </div>
              <div style="display: flex; justify-content: space-between; font-size: 0.8rem; background: rgba(0, 0, 0, 0.25); padding: 0.5rem 0.75rem; border-radius: 4px;">
                <div><span style="color: var(--text-muted);">Habla:</span> <strong style="color: #38BDF8;">${l.listening_level || "Regular"}</strong></div>
                <div><span style="color: var(--text-muted);">Lectura:</span> <strong style="color: #38BDF8;">${l.reading_level || "Bien"}</strong></div>
                <div><span style="color: var(--text-muted);">Escritura:</span> <strong style="color: #38BDF8;">${l.writing_level || "Bien"}</strong></div>
              </div>
            </div>
          `).join("")}
        </div>
      `;
    } else {
      langEl.innerHTML = `<div style="color: var(--text-muted); padding: 2rem; text-align: center;">No se registraron idiomas adicionales.</div>`;
    }
  }

  // Attach Traceability Click Handlers across all tabs
  attachTraceabilityClick(container, pdfViewer);
}

function renderFieldCard(
  label: string,
  value: string,
  pageNumber: number,
  highlight = false,
  colSpan = 1
): string {
  return `
    <div class="traceable-card traceable-row" data-page="${pageNumber}" style="${colSpan > 1 ? `grid-column: span ${colSpan};` : ''} ${highlight ? 'border-color: rgba(56, 189, 248, 0.4); background: rgba(56, 189, 248, 0.05);' : ''} padding: 0.85rem 1rem; border-radius: var(--radius-sm);">
      <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.45rem; gap: 0.5rem;">
        <span style="font-size: 0.725rem; font-weight: 600; color: ${highlight ? '#38BDF8' : 'var(--text-muted)'}; text-transform: uppercase; letter-spacing: 0.5px;">
          ${label}
        </span>
        <span class="badge" style="background: rgba(255, 255, 255, 0.06); color: var(--text-secondary); font-size: 0.7rem; padding: 0.15rem 0.45rem; border-radius: 4px; font-weight: 500; font-family: var(--font-mono); white-space: nowrap;">
          Pág. ${pageNumber}
        </span>
      </div>
      <div style="font-size: 0.925rem; font-weight: ${highlight ? '600' : '500'}; color: ${highlight ? '#38BDF8' : '#FFF'}; word-break: break-word; line-height: 1.45;">
        ${value}
      </div>
    </div>
  `;
}

function attachTraceabilityClick(container: HTMLElement, pdfViewer: PdfViewer): void {
  const rows = container.querySelectorAll(".traceable-row");
  rows.forEach((row) => {
    row.addEventListener("click", () => {
      const pageNumStr = (row as HTMLElement).dataset.page;
      if (pageNumStr) {
        const pageNum = parseInt(pageNumStr, 10);
        if (pageNum > 0) {
          pdfViewer.goToPage(pageNum);
          Toast.info(`Navegando a la página ${pageNum} del documento original`);
        }
      }
    });
  });
}

async function loadReviewFields(container: HTMLElement, documentId: string, pdfViewer: PdfViewer): Promise<void> {
  const reviewContainer = container.querySelector("#review-fields-container");
  const reviewBadge = container.querySelector("#badge-count-review");
  if (!reviewContainer) return;

  try {
    const fields: ReviewField[] = await reviewService.getFieldsForDocument(documentId);
    if (reviewBadge) {
      reviewBadge.textContent = (fields?.length || 0).toString();
    }

    if (!fields || fields.length === 0) {
      reviewContainer.innerHTML = `
        <div style="text-align: center; padding: 2.5rem; color: var(--text-muted); font-size: 0.85rem;">
          No hay campos que requieran revisión humana para este documento.
        </div>
      `;
      return;
    }

    reviewContainer.innerHTML = fields.map((field) => `
      <div class="card" style="padding: 0.85rem 1rem; background: var(--bg-surface-elevated); border: 1px solid ${field.review_status === 'PENDING' ? 'rgba(245, 158, 11, 0.4)' : 'var(--border-subtle)'};" data-field-id="${field.id}">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.4rem;">
          <div>
            <strong style="color: #38BDF8; font-size: 0.85rem;">${field.field_name}</strong>
            <span style="font-size: 0.75rem; color: var(--text-muted); margin-left: 0.5rem; cursor: pointer;" class="btn-jump-page" data-page="${field.page_number}">
              (Pág. ${field.page_number})
            </span>
          </div>
          <div style="display: flex; align-items: center; gap: 0.5rem;">
            <span class="badge" style="font-family: var(--font-mono); font-size: 0.725rem; background: ${field.confidence < 0.7 ? 'rgba(239, 68, 68, 0.2)' : 'rgba(16, 185, 129, 0.2)'}; color: ${field.confidence < 0.7 ? '#F87171' : '#34D399'};">
              Confianza: ${Math.round(field.confidence * 100)}%
            </span>
            <span class="badge badge-${field.review_status === 'ACCEPTED' ? 'success' : field.review_status === 'CORRECTED' ? 'info' : field.review_status === 'REJECTED' ? 'danger' : 'warning'}">
              ${field.review_status}
            </span>
          </div>
        </div>

        <div style="font-size: 0.825rem; color: var(--text-secondary); margin-bottom: 0.6rem;">
          <strong>Valor Extraído:</strong> ${field.raw_value || "(vacío)"}
          ${field.corrected_value ? `<br><strong style="color: var(--color-success);">Valor Corregido:</strong> ${field.corrected_value}` : ""}
        </div>

        <!-- Action Controls -->
        <div style="display: flex; gap: 0.4rem; justify-content: flex-end;">
          <button class="btn btn-outline btn-sm btn-accept-field" data-id="${field.id}" style="color: #34D399; font-size: 0.75rem; padding: 0.2rem 0.6rem;">
            Aceptar
          </button>
          <button class="btn btn-outline btn-sm btn-correct-field" data-id="${field.id}" data-current="${field.raw_value || ''}" style="color: #38BDF8; font-size: 0.75rem; padding: 0.2rem 0.6rem;">
            Corregir
          </button>
          <button class="btn btn-outline btn-sm btn-reject-field" data-id="${field.id}" style="color: #F87171; font-size: 0.75rem; padding: 0.2rem 0.6rem;">
            Rechazar
          </button>
        </div>
      </div>
    `).join("");

    // Wire Review Field Actions
    reviewContainer.querySelectorAll(".btn-jump-page").forEach((el) => {
      el.addEventListener("click", () => {
        const p = parseInt((el as HTMLElement).dataset.page || "1", 10);
        pdfViewer.goToPage(p);
      });
    });

    reviewContainer.querySelectorAll(".btn-accept-field").forEach((btn) => {
      btn.addEventListener("click", async () => {
        const id = (btn as HTMLElement).dataset.id!;
        try {
          await reviewService.acceptField(documentId, id);
          Toast.success("Campo aceptado.");
          loadReviewFields(container, documentId, pdfViewer);
        } catch (err: any) {
          Toast.error(err.message || "Error al aceptar campo.");
        }
      });
    });

    reviewContainer.querySelectorAll(".btn-correct-field").forEach((btn) => {
      btn.addEventListener("click", async () => {
        const id = (btn as HTMLElement).dataset.id!;
        const current = (btn as HTMLElement).dataset.current || "";
        const newVal = prompt("Ingrese el valor correcto para este campo:", current);
        if (newVal !== null && newVal.trim() !== "") {
          try {
            await reviewService.correctField(documentId, id, newVal.trim());
            Toast.success("Campo corregido exitosamente.");
            loadReviewFields(container, documentId, pdfViewer);
          } catch (err: any) {
            Toast.error(err.message || "Error al corregir campo.");
          }
        }
      });
    });

    reviewContainer.querySelectorAll(".btn-reject-field").forEach((btn) => {
      btn.addEventListener("click", async () => {
        const id = (btn as HTMLElement).dataset.id!;
        const reason = prompt("Indique el motivo del rechazo del campo:", "Extracción errónea o ilegible");
        if (reason !== null) {
          try {
            await reviewService.rejectField(documentId, id, reason);
            Toast.info("Campo marcado como rechazado.");
            loadReviewFields(container, documentId, pdfViewer);
          } catch (err: any) {
            Toast.error(err.message || "Error al rechazar campo.");
          }
        }
      });
    });

  } catch (err: any) {
    reviewContainer.innerHTML = `<div style="color: var(--color-danger); padding: 1rem;">Error al cargar campos de revisión.</div>`;
  }
}

function wireActionButtons(container: HTMLElement, documentId: string, pdfViewer: PdfViewer): void {
  const btnReclassify = container.querySelector("#btn-reclassify");
  const btnExtractDafp = container.querySelector("#btn-extract-dafp");
  const btnExtractAts = container.querySelector("#btn-extract-ats");
  const btnDownloadPdf = container.querySelector("#btn-download-pdf");
  const btnFinalize = container.querySelector("#btn-finalize-review");

  btnReclassify?.addEventListener("click", async () => {
    try {
      Toast.info("Ejecutando clasificador...");
      const res = await documentService.classify(documentId);
      Toast.success(`Clasificación completada: ${res.document_type || "DETECTADO"}`);
      loadFullDocumentView(container, documentId, pdfViewer);
    } catch (err: any) {
      Toast.error(err.message || "Error al clasificar documento.");
    }
  });

  btnExtractDafp?.addEventListener("click", async () => {
    try {
      Toast.info("Extrayendo estructura DAFP...");
      await documentService.extractFormatoUnico(documentId);
      Toast.success("Extracción Formato Único completada exitosamente.");
      loadFullDocumentView(container, documentId, pdfViewer);
    } catch (err: any) {
      Toast.error(err.message || "Error al extraer Formato Único.");
    }
  });

  btnExtractAts?.addEventListener("click", async () => {
    try {
      Toast.info("Extrayendo estructura ATS...");
      await documentService.extractAts(documentId);
      Toast.success("Extracción ATS completada exitosamente.");
      loadFullDocumentView(container, documentId, pdfViewer);
    } catch (err: any) {
      Toast.error(err.message || "Error al extraer formato ATS.");
    }
  });

  btnDownloadPdf?.addEventListener("click", async () => {
    try {
      const blob = await documentService.downloadBlob(documentId);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `documento_${documentId.substring(0, 8)}.pdf`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (err: any) {
      Toast.error("Error al descargar el archivo PDF original.");
    }
  });

  btnFinalize?.addEventListener("click", async () => {
    if (confirm("¿Desea dar por finalizado el ciclo de revisión de esta hoja de vida?")) {
      try {
        await reviewService.finalizeReview(documentId);
        Toast.success("Ciclo de revisión humana finalizado exitosamente.");
        loadFullDocumentView(container, documentId, pdfViewer);
      } catch (err: any) {
        Toast.error(err.message || "Error al finalizar revisión.");
      }
    }
  });
}

function renderEmptyCanonical(container: HTMLElement): void {
  const personalEl = container.querySelector("#personal-fields");
  if (personalEl) {
    personalEl.innerHTML = `
      <div style="grid-column: 1 / -1; text-align: center; padding: 3rem 1rem; color: var(--text-muted);">
        <p style="margin-bottom: 0.5rem; font-weight: 500;">Este documento aún no cuenta con datos canónicos extraídos.</p>
        <p style="font-size: 0.8rem;">Utilice los botones "Extraer DAFP" o "Extraer ATS" en la barra superior para iniciar el procesamiento.</p>
      </div>
    `;
  }
}
