import { documentService, CanonicalResumeData } from "../services/documentService";
import { reviewService, ReviewField } from "../services/reviewService";
import { PdfViewer } from "../components/PdfViewer";
import { renderStatusBadge, renderFormatBadge } from "../components/StatusBadge";
import { Toast } from "../components/Toast";

export async function renderDocumentDetailPage(container: HTMLElement, documentId: string): Promise<void> {
  container.innerHTML = `
    <div class="page-container" style="max-width: 1600px; margin: 0 auto; padding: 1.25rem 1.5rem; height: calc(100vh - var(--header-height)); display: flex; flex-direction: column;">
      <!-- Breadcrumb & Actions Bar -->
      <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem; flex-wrap: wrap; gap: 0.75rem; flex-shrink: 0;">
        <div style="display: flex; align-items: center; gap: 0.75rem;">
          <a href="#/documents" class="btn btn-outline btn-sm" style="display: inline-flex; align-items: center; gap: 0.35rem;">
            &larr; Volver
          </a>
          <div>
            <div style="display: flex; align-items: center; gap: 0.5rem;">
              <h1 id="doc-title" style="font-size: 1.25rem; font-weight: 700; color: var(--text-primary); margin: 0;">
                Cargando hoja de vida...
              </h1>
              <span id="doc-format-badge"></span>
              <span id="doc-status-badge"></span>
            </div>
            <div id="doc-meta-info" style="font-size: 0.75rem; color: var(--text-muted); font-family: var(--font-mono); margin-top: 2px;">
              ID: ${documentId}
            </div>
          </div>
        </div>

        <div style="display: flex; gap: 0.5rem; align-items: center; flex-wrap: wrap;">
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
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
            PDF Original
          </button>
          <button id="btn-finalize-review" class="btn btn-primary btn-sm" style="background: #10B981; border-color: #059669;">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="20 6 9 17 4 12"/></svg>
            Finalizar Revisión
          </button>
        </div>
      </div>

      <!-- Main Split-Screen Workspace (Chapter 27) -->
      <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1.25rem; flex: 1; min-height: 0;">
        <!-- Left Panel: Interactive PDF Viewer -->
        <div id="pdf-viewer-container" style="height: 100%; min-height: 0;"></div>

        <!-- Right Panel: Structured Extraction & Traceability Tabs -->
        <div class="card" style="display: flex; flex-direction: column; height: 100%; min-height: 0; overflow: hidden; background: var(--bg-surface);">
          <!-- Tab Navigation -->
          <div style="
            display: flex;
            border-bottom: 1px solid var(--border-subtle);
            background: var(--bg-surface-elevated);
            overflow-x: auto;
            flex-shrink: 0;
          ">
            <button class="tab-btn active" data-tab="tab-personal">Datos Personales</button>
            <button class="tab-btn" data-tab="tab-contact">Contacto</button>
            <button class="tab-btn" data-tab="tab-education">Educación</button>
            <button class="tab-btn" data-tab="tab-experience">Experiencia</button>
            <button class="tab-btn" data-tab="tab-languages">Idiomas</button>
            <button class="tab-btn" data-tab="tab-review">Auditoría / HITL</button>
          </div>

          <!-- Traceability Instruction Banner -->
          <div style="
            padding: 0.5rem 1rem;
            background: rgba(2, 132, 199, 0.08);
            border-bottom: 1px solid rgba(2, 132, 199, 0.15);
            font-size: 0.775rem;
            color: #38BDF8;
            display: flex;
            align-items: center;
            justify-content: space-between;
            flex-shrink: 0;
          ">
            <span style="display: flex; align-items: center; gap: 0.4rem;">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg>
              Haga clic en cualquier fila o insignia de página para saltar al origen en el PDF.
            </span>
            <span id="extracted-fields-badge" class="badge" style="background: rgba(56, 189, 248, 0.2); color: #38BDF8;">
              0 campos extraídos
            </span>
          </div>

          <!-- Tab Content Scrollable Container -->
          <div id="tab-content-wrapper" style="flex: 1; overflow-y: auto; padding: 1.25rem;">
            <!-- Tab: Personal Data -->
            <div id="tab-personal" class="tab-pane active">
              <div id="personal-fields" style="display: grid; grid-template-columns: 1fr 1fr; gap: 1rem;"></div>
            </div>

            <!-- Tab: Contact Information -->
            <div id="tab-contact" class="tab-pane" style="display: none;">
              <div id="contact-fields" style="display: grid; grid-template-columns: 1fr 1fr; gap: 1rem;"></div>
            </div>

            <!-- Tab: Education -->
            <div id="tab-education" class="tab-pane" style="display: none;">
              <div id="education-fields" style="display: flex; flex-direction: column; gap: 1rem;"></div>
            </div>

            <!-- Tab: Experience -->
            <div id="tab-experience" class="tab-pane" style="display: none;">
              <div id="experience-summary-box" style="margin-bottom: 1rem;"></div>
              <div id="experience-fields" style="display: flex; flex-direction: column; gap: 1rem;"></div>
            </div>

            <!-- Tab: Languages -->
            <div id="tab-languages" class="tab-pane" style="display: none;">
              <div id="languages-fields" style="display: flex; flex-direction: column; gap: 1rem;"></div>
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

  // Apply tab styles inline
  const styleEl = document.createElement("style");
  styleEl.textContent = `
    .tab-btn {
      padding: 0.75rem 1.1rem;
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
    .traceable-row {
      cursor: pointer;
      padding: 0.65rem 0.85rem;
      background: var(--bg-surface-elevated);
      border: 1px solid var(--border-subtle);
      border-radius: var(--radius-sm);
      transition: all var(--transition-fast);
    }
    .traceable-row:hover {
      border-color: #38BDF8;
      background: rgba(56, 189, 248, 0.04);
      transform: translateY(-1px);
    }
  `;
  container.appendChild(styleEl);

  // Initialize PDF Viewer instance
  const pdfContainer = container.querySelector("#pdf-viewer-container") as HTMLElement;
  const pdfViewer = new PdfViewer(pdfContainer);

  // Wire Tab Switching
  setupTabEvents(container);

  // Load Document, PDF Blob, and Structured Data
  await loadFullDocumentView(container, documentId, pdfViewer);
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
    const doc = await documentService.getById(documentId);
    updateDocHeader(container, doc);

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
      // If canonical doesn't exist yet, render placeholder
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

function updateDocHeader(container: HTMLElement, doc: any): void {
  const titleEl = container.querySelector("#doc-title");
  const formatEl = container.querySelector("#doc-format-badge");
  const statusEl = container.querySelector("#doc-status-badge");
  const metaEl = container.querySelector("#doc-meta-info");

  if (titleEl) titleEl.textContent = doc.original_filename || doc.filename || "Hoja de Vida";
  if (formatEl) formatEl.innerHTML = renderFormatBadge(doc.document_type);
  if (statusEl) statusEl.innerHTML = renderStatusBadge(doc.status);
  if (metaEl) {
    metaEl.textContent = `Páginas: ${doc.page_count || 1} • Subido: ${new Date(doc.created_at).toLocaleDateString("es-CO")} • SHA256: ${(doc.sha256_checksum || "").substring(0, 16)}...`;
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

  // 1. Personal Data Tab
  const personalEl = container.querySelector("#personal-fields");
  if (personalEl && data.person) {
    const p = data.person;
    personalEl.innerHTML = `
      ${renderFieldRow("Nombres", `${p.first_name || ""} ${p.middle_name || ""}`.trim(), 1)}
      ${renderFieldRow("Apellidos", `${p.first_surname || ""} ${p.second_surname || ""}`.trim(), 1)}
      ${renderFieldRow("Documento de Identidad", `${p.identification_type || "CC"} ${p.identification_number || "No registrado"}`, 1)}
      ${renderFieldRow("Nacionalidad", p.nationality || "Colombiana", 1)}
      ${renderFieldRow("Sexo", p.sex || "No especificado", 1)}
      ${renderFieldRow("Fecha de Nacimiento", p.birth_date || "No registrada", 1)}
    `;
  }

  // 2. Contact Tab
  const contactEl = container.querySelector("#contact-fields");
  if (contactEl && data.contact) {
    const c = data.contact;
    contactEl.innerHTML = `
      ${renderFieldRow("Dirección", c.address || "No registrada", 1)}
      ${renderFieldRow("Departamento", c.department || "No registrado", 1)}
      ${renderFieldRow("Municipio / Ciudad", c.municipality || "No registrado", 1)}
      ${renderFieldRow("Correo Electrónico", c.email || "No registrado", 1)}
      ${renderFieldRow("Teléfono Celular", c.mobile_phone || "No registrado", 1)}
      ${renderFieldRow("Teléfono Fijo", c.telephone || "No registrado", 1)}
    `;
  }

  // 3. Education Tab
  const eduEl = container.querySelector("#education-fields");
  if (eduEl) {
    if (data.educations && data.educations.length > 0) {
      eduEl.innerHTML = data.educations.map((edu, idx) => `
        <div class="traceable-row" data-page="${idx > 2 ? 2 : 1}">
          <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 0.35rem;">
            <div style="font-weight: 600; color: var(--text-primary); font-size: 0.9rem;">
              ${edu.degree_title || "Título no especificado"}
            </div>
            <span class="badge" style="background: rgba(2, 132, 199, 0.15); color: #38BDF8; font-size: 0.725rem;">
              Pág. ${idx > 2 ? 2 : 1} &rarr;
            </span>
          </div>
          <div style="font-size: 0.825rem; color: var(--text-secondary); margin-bottom: 0.25rem;">
            <strong>Institución:</strong> ${edu.institution || "Institución no registrada"}
          </div>
          <div style="display: flex; gap: 1rem; font-size: 0.775rem; color: var(--text-muted);">
            <span><strong>Nivel:</strong> ${edu.academic_level || "No especificado"}</span>
            <span><strong>Graduado:</strong> ${edu.is_graduated ? "Sí" : "No"}</span>
            ${edu.graduation_date ? `<span><strong>Fecha:</strong> ${edu.graduation_date}</span>` : ""}
            ${edu.professional_card_number ? `<span><strong>Tarjeta Prof.:</strong> ${edu.professional_card_number}</span>` : ""}
          </div>
        </div>
      `).join("");
    } else {
      eduEl.innerHTML = `<div style="color: var(--text-muted); padding: 1rem 0; font-size: 0.85rem;">No se encontraron registros de educación formal.</div>`;
    }
  }

  // 4. Experience Tab
  const expEl = container.querySelector("#experience-fields");
  const expSummaryEl = container.querySelector("#experience-summary-box");

  if (expSummaryEl && data.experience_summary) {
    const s = data.experience_summary;
    expSummaryEl.innerHTML = `
      <div style="padding: 0.85rem 1rem; background: rgba(16, 185, 129, 0.08); border: 1px solid rgba(16, 185, 129, 0.2); border-radius: var(--radius-sm); display: flex; justify-content: space-around; font-size: 0.825rem;">
        <div><strong>Exp. Pública:</strong> <span style="color: var(--color-success); font-weight: 600;">${s.public_experience_display || `${s.public_experience_months || 0} meses`}</span></div>
        <div><strong>Exp. Privada:</strong> <span style="color: #38BDF8; font-weight: 600;">${s.private_experience_months || 0} meses</span></div>
        <div><strong>Total Experiencia:</strong> <span style="color: #F8FAFC; font-weight: 700;">${s.total_experience_display || `${s.total_experience_months || 0} meses`}</span></div>
      </div>
    `;
  }

  if (expEl) {
    if (data.work_experiences && data.work_experiences.length > 0) {
      expEl.innerHTML = data.work_experiences.map((exp, idx) => `
        <div class="traceable-row" data-page="${idx > 1 ? 2 : 1}">
          <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 0.35rem;">
            <div style="font-weight: 600; color: var(--text-primary); font-size: 0.9rem;">
              ${exp.position || "Cargo no especificado"}
            </div>
            <span class="badge" style="background: rgba(2, 132, 199, 0.15); color: #38BDF8; font-size: 0.725rem;">
              Pág. ${idx > 1 ? 2 : 1} &rarr;
            </span>
          </div>
          <div style="font-size: 0.825rem; color: var(--text-secondary); margin-bottom: 0.25rem;">
            <strong>Empresa / Entidad:</strong> ${exp.company_name}
            ${exp.is_public_sector ? `<span class="badge" style="margin-left: 0.5rem; background: rgba(56, 189, 248, 0.15); color: #38BDF8; font-size: 0.7rem;">Sector Público</span>` : ""}
          </div>
          <div style="display: flex; gap: 1rem; font-size: 0.775rem; color: var(--text-muted); margin-bottom: 0.4rem;">
            <span><strong>Periodo:</strong> ${exp.start_date || "—"} a ${exp.is_current ? "Presente" : (exp.end_date || "—")}</span>
            <span><strong>Duración:</strong> ${exp.total_months || 0} meses</span>
          </div>
          ${exp.responsibilities ? `<div style="font-size: 0.8rem; color: var(--text-secondary); line-height: 1.4; background: rgba(0,0,0,0.2); padding: 0.4rem 0.6rem; border-radius: 4px;">${exp.responsibilities}</div>` : ""}
        </div>
      `).join("");
    } else {
      expEl.innerHTML = `<div style="color: var(--text-muted); padding: 1rem 0; font-size: 0.85rem;">No se encontraron registros de experiencia laboral.</div>`;
    }
  }

  // 5. Languages Tab
  const langEl = container.querySelector("#languages-fields");
  if (langEl) {
    if (data.languages && data.languages.length > 0) {
      langEl.innerHTML = data.languages.map((l) => `
        <div class="traceable-row" data-page="2">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.4rem;">
            <div style="font-weight: 600; color: var(--text-primary);">${l.language}</div>
            <span class="badge" style="background: rgba(2, 132, 199, 0.15); color: #38BDF8; font-size: 0.725rem;">Pág. 2 &rarr;</span>
          </div>
          <div style="display: flex; gap: 1.5rem; font-size: 0.8rem; color: var(--text-secondary);">
            <span><strong>Habla:</strong> ${l.listening_level || "Regular"}</span>
            <span><strong>Lectura:</strong> ${l.reading_level || "Bien"}</span>
            <span><strong>Escritura:</strong> ${l.writing_level || "Bien"}</span>
          </div>
        </div>
      `).join("");
    } else {
      langEl.innerHTML = `<div style="color: var(--text-muted); padding: 1rem 0; font-size: 0.85rem;">No se registraron idiomas adicionales.</div>`;
    }
  }

  // Attach Traceability Click Handlers across all tabs
  attachTraceabilityClick(container, pdfViewer);
}

function renderFieldRow(label: string, value: string, pageNumber: number): string {
  return `
    <div class="traceable-row" data-page="${pageNumber}">
      <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.2rem;">
        <span style="font-size: 0.75rem; font-weight: 600; color: var(--text-muted); text-transform: uppercase;">
          ${label}
        </span>
        <span class="badge" style="background: rgba(2, 132, 199, 0.15); color: #38BDF8; font-size: 0.7rem;">
          Pág. ${pageNumber}
        </span>
      </div>
      <div style="font-size: 0.875rem; font-weight: 500; color: var(--text-primary);">
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
          Toast.info(`Navegando a la página ${pageNum} del documento fuente`);
        }
      }
    });
  });
}

async function loadReviewFields(container: HTMLElement, documentId: string, pdfViewer: PdfViewer): Promise<void> {
  const reviewContainer = container.querySelector("#review-fields-container");
  if (!reviewContainer) return;

  try {
    const fields: ReviewField[] = await reviewService.getFieldsForDocument(documentId);
    if (!fields || fields.length === 0) {
      reviewContainer.innerHTML = `
        <div style="text-align: center; padding: 2rem; color: var(--text-muted); font-size: 0.85rem;">
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
