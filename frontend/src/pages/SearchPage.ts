import { searchService, CandidateItem, CandidateFullDetail, FilterOptionsResponse } from "../services/searchService";
import { renderPagination } from "../components/Pagination";
import { Toast } from "../components/Toast";

export async function renderSearchPage(container: HTMLElement): Promise<void> {
  container.innerHTML = `
    <div class="page-container" style="max-width: 1500px; margin: 0 auto; padding: 1.5rem;">
      <!-- Header -->
      <div style="margin-bottom: 1.5rem;">
        <div style="font-size: 0.8rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.08em; color: #38BDF8; margin-bottom: 0.35rem;">
          Motor de Búsqueda Multicriterio
        </div>
        <h1 style="font-size: 1.75rem; font-weight: 700; color: var(--text-primary); margin: 0;">
          Consulta de Candidatos y Perfiles Profesionales
        </h1>
        <p style="font-size: 0.9rem; color: var(--text-secondary); margin-top: 0.25rem;">
          Filtre la base de datos de talento por profesión, nivel académico, departamento y experiencia laboral comprobada.
        </p>
      </div>

      <!-- Search Input Bar -->
      <div class="card" style="padding: 1.25rem; margin-bottom: 1.5rem;">
        <div style="display: flex; gap: 0.75rem;">
          <div style="position: relative; flex: 1;">
            <input 
              type="text" 
              id="search-query" 
              class="form-control" 
              placeholder="Buscar por nombre, cédula, cargo, habilidades o palabras clave..."
              style="width: 100%; padding: 0.75rem 1rem 0.75rem 2.5rem; font-size: 0.95rem; background: #0B1120; border: 1px solid var(--border-subtle); color: #FFF; border-radius: var(--radius-sm);"
            />
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="position: absolute; left: 0.85rem; top: 50%; transform: translateY(-50%); color: var(--text-muted);">
              <circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>
            </svg>
          </div>
          <button id="btn-search-submit" class="btn btn-primary" style="padding: 0.75rem 1.5rem; font-weight: 600;">
            Buscar
          </button>
          <button id="btn-search-reset" class="btn btn-outline" style="padding: 0.75rem 1rem;" title="Limpiar filtros">
            Reiniciar
          </button>
        </div>
      </div>

      <!-- Main Layout: Sidebar Facets + Results Grid -->
      <div style="display: grid; grid-template-columns: 280px 1fr; gap: 1.5rem; align-items: start;">
        <!-- Left Sidebar: Filters & Facets -->
        <div class="card" style="padding: 1.25rem;">
          <div style="font-size: 0.85rem; font-weight: 700; color: var(--text-primary); text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 1rem; border-bottom: 1px solid var(--border-subtle); padding-bottom: 0.5rem;">
            Filtros Avanzados
          </div>

          <!-- Category Filter -->
          <div class="form-group" style="margin-bottom: 1.1rem;">
            <label class="form-label" style="font-size: 0.8rem; font-weight: 600; color: var(--text-secondary); margin-bottom: 0.35rem; display: block;">
              Área / Categoría
            </label>
            <select id="facet-category" class="form-control" style="width: 100%; padding: 0.45rem 0.65rem; font-size: 0.825rem; background: #0B1120; border: 1px solid var(--border-subtle); color: #FFF; border-radius: var(--radius-sm);">
              <option value="">Todas las categorías</option>
            </select>
          </div>

          <!-- Profession Filter -->
          <div class="form-group" style="margin-bottom: 1.1rem;">
            <label class="form-label" style="font-size: 0.8rem; font-weight: 600; color: var(--text-secondary); margin-bottom: 0.35rem; display: block;">
              Profesión
            </label>
            <select id="facet-profession" class="form-control" style="width: 100%; padding: 0.45rem 0.65rem; font-size: 0.825rem; background: #0B1120; border: 1px solid var(--border-subtle); color: #FFF; border-radius: var(--radius-sm);">
              <option value="">Todas las profesiones</option>
            </select>
          </div>

          <!-- Academic Level Filter -->
          <div class="form-group" style="margin-bottom: 1.1rem;">
            <label class="form-label" style="font-size: 0.8rem; font-weight: 600; color: var(--text-secondary); margin-bottom: 0.35rem; display: block;">
              Nivel Académico
            </label>
            <select id="facet-level" class="form-control" style="width: 100%; padding: 0.45rem 0.65rem; font-size: 0.825rem; background: #0B1120; border: 1px solid var(--border-subtle); color: #FFF; border-radius: var(--radius-sm);">
              <option value="">Cualquier nivel</option>
            </select>
          </div>

          <!-- Department Filter -->
          <div class="form-group" style="margin-bottom: 1.1rem;">
            <label class="form-label" style="font-size: 0.8rem; font-weight: 600; color: var(--text-secondary); margin-bottom: 0.35rem; display: block;">
              Departamento
            </label>
            <select id="facet-department" class="form-control" style="width: 100%; padding: 0.45rem 0.65rem; font-size: 0.825rem; background: #0B1120; border: 1px solid var(--border-subtle); color: #FFF; border-radius: var(--radius-sm);">
              <option value="">Todos los departamentos</option>
            </select>
          </div>

          <!-- Experience Range Filter -->
          <div class="form-group" style="margin-bottom: 1.25rem;">
            <label class="form-label" style="font-size: 0.8rem; font-weight: 600; color: var(--text-secondary); margin-bottom: 0.35rem; display: block;">
              Años de Experiencia Mínima
            </label>
            <input 
              type="number" 
              id="facet-min-exp" 
              class="form-control" 
              min="0" 
              max="50" 
              placeholder="Ej. 2"
              style="width: 100%; padding: 0.45rem 0.65rem; font-size: 0.825rem; background: #0B1120; border: 1px solid var(--border-subtle); color: #FFF; border-radius: var(--radius-sm);"
            />
          </div>

          <button id="btn-filter-apply" class="btn btn-outline btn-sm" style="width: 100%; justify-content: center;">
            Aplicar Filtros
          </button>
        </div>

        <!-- Right Content: Results Counter & Cards -->
        <div>
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem;">
            <div id="results-count" style="font-size: 0.875rem; color: var(--text-secondary);">
              Cargando candidatos...
            </div>
            <div style="display: flex; align-items: center; gap: 0.5rem; font-size: 0.825rem;">
              <span style="color: var(--text-muted);">Ordenar:</span>
              <select id="sort-select" style="background: #0B1120; border: 1px solid var(--border-subtle); color: #FFF; padding: 0.25rem 0.5rem; border-radius: var(--radius-sm); font-size: 0.825rem;">
                <option value="name_asc">Nombre (A-Z)</option>
                <option value="exp_desc">Mayor Experiencia</option>
              </select>
            </div>
          </div>

          <!-- Results Cards Grid -->
          <div id="candidates-grid" style="display: grid; grid-template-columns: repeat(auto-fill, minmax(340px, 1fr)); gap: 1rem; margin-bottom: 1.5rem;"></div>

          <!-- Pagination -->
          <div id="search-pagination"></div>
        </div>
      </div>

      <!-- Dossier Modal Container -->
      <div id="dossier-modal-backdrop" style="display: none; position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0, 0, 0, 0.75); backdrop-filter: blur(4px); z-index: 100; align-items: center; justify-content: center; padding: 1.5rem;">
        <div class="card card-elevated" style="width: 100%; max-width: 800px; max-height: 90vh; display: flex; flex-direction: column; overflow: hidden; background: #0F172A; border: 1px solid var(--border-subtle);">
          <div style="padding: 1.25rem 1.5rem; border-bottom: 1px solid var(--border-subtle); display: flex; justify-content: space-between; align-items: center;">
            <h2 id="dossier-modal-name" style="font-size: 1.2rem; font-weight: 700; color: var(--text-primary); margin: 0;">
              Dossier Integral del Candidato
            </h2>
            <button id="btn-close-dossier" class="btn btn-outline btn-sm" style="padding: 0.25rem 0.6rem;">&times;</button>
          </div>
          <div id="dossier-modal-body" style="flex: 1; overflow-y: auto; padding: 1.5rem;"></div>
        </div>
      </div>
    </div>
  `;

  let currentPage = 1;
  const pageSize = 12;

  // Cached taxonomy for cascading dropdowns
  let allProfessionsList: Array<{ id: string; name: string; category_id?: string }> = [];

  const updateProfessionOptions = (selectedCatId?: string) => {
    const profSelect = container.querySelector("#facet-profession") as HTMLSelectElement;
    if (!profSelect) return;
    const currentVal = profSelect.value;
    profSelect.innerHTML = `<option value="">Todas las profesiones</option>`;
    const filtered = selectedCatId
      ? allProfessionsList.filter((p) => p.category_id === selectedCatId)
      : allProfessionsList;

    filtered.forEach((p) => {
      const opt = document.createElement("option");
      opt.value = p.id;
      opt.textContent = p.name;
      if (p.id === currentVal) opt.selected = true;
      profSelect.appendChild(opt);
    });
  };

  // Load Filter Options
  await loadFilterOptions(container, (profs) => {
    allProfessionsList = profs;
    updateProfessionOptions();
  });

  // Setup Event Handlers
  const queryInput = container.querySelector("#search-query") as HTMLInputElement;
  const btnSearch = container.querySelector("#btn-search-submit");
  const btnReset = container.querySelector("#btn-search-reset");
  const btnFilterApply = container.querySelector("#btn-filter-apply");
  const sortSelect = container.querySelector("#sort-select") as HTMLSelectElement;
  const catSelect = container.querySelector("#facet-category") as HTMLSelectElement;
  const profSelect = container.querySelector("#facet-profession") as HTMLSelectElement;

  const triggerSearch = () => {
    currentPage = 1;
    executeSearch(container, currentPage, pageSize);
  };

  btnSearch?.addEventListener("click", triggerSearch);
  queryInput?.addEventListener("keydown", (e) => {
    if (e.key === "Enter") triggerSearch();
  });
  btnFilterApply?.addEventListener("click", triggerSearch);
  sortSelect?.addEventListener("change", triggerSearch);

  catSelect?.addEventListener("change", () => {
    updateProfessionOptions(catSelect.value);
    triggerSearch();
  });

  profSelect?.addEventListener("change", () => {
    if (profSelect.value) {
      const matched = allProfessionsList.find((p) => p.id === profSelect.value);
      if (matched && matched.category_id && !catSelect.value) {
        catSelect.value = matched.category_id;
      }
    }
    triggerSearch();
  });

  btnReset?.addEventListener("click", () => {
    queryInput.value = "";
    if (catSelect) catSelect.value = "";
    updateProfessionOptions("");
    if (profSelect) profSelect.value = "";
    (container.querySelector("#facet-level") as HTMLSelectElement).value = "";
    (container.querySelector("#facet-department") as HTMLSelectElement).value = "";
    (container.querySelector("#facet-min-exp") as HTMLInputElement).value = "";
    triggerSearch();
  });

  // Wire Modal Close
  const modalBackdrop = container.querySelector("#dossier-modal-backdrop") as HTMLElement;
  container.querySelector("#btn-close-dossier")?.addEventListener("click", () => {
    modalBackdrop.style.display = "none";
  });
  modalBackdrop?.addEventListener("click", (e) => {
    if (e.target === modalBackdrop) modalBackdrop.style.display = "none";
  });

  // Initial Search
  await executeSearch(container, currentPage, pageSize);
}

async function loadFilterOptions(
  container: HTMLElement,
  onProfessionsLoaded?: (profs: Array<{ id: string; name: string; category_id?: string }>) => void
): Promise<void> {
  try {
    const opts: FilterOptionsResponse = await searchService.getFilterOptions();
    const catSelect = container.querySelector("#facet-category") as HTMLSelectElement;
    const lvlSelect = container.querySelector("#facet-level") as HTMLSelectElement;
    const dptSelect = container.querySelector("#facet-department") as HTMLSelectElement;

    if (catSelect && opts.categories) {
      opts.categories.forEach((c) => {
        const opt = document.createElement("option");
        opt.value = c.id;
        opt.textContent = c.name;
        catSelect.appendChild(opt);
      });
    }

    const LEVEL_LABELS: Record<string, string> = {
      BASIC: "Básica Primaria",
      SECONDARY: "Secundaria",
      HIGH_SCHOOL: "Bachiller / Media",
      TECHNICAL: "Técnico Laboral",
      TECHNOLOGIST: "Tecnólogo",
      UNDERGRADUATE: "Profesional / Pregrado",
      SPECIALIZATION: "Especialización",
      MASTER: "Maestría",
      DOCTORATE: "Doctorado",
      OTHER: "Otro",
    };

    if (lvlSelect && opts.academic_levels) {
      opts.academic_levels.forEach((l) => {
        const opt = document.createElement("option");
        opt.value = l;
        opt.textContent = LEVEL_LABELS[l] || l;
        lvlSelect.appendChild(opt);
      });
    }

    if (dptSelect && opts.departments) {
      opts.departments.forEach((d) => {
        const opt = document.createElement("option");
        opt.value = d;
        opt.textContent = d;
        dptSelect.appendChild(opt);
      });
    }

    // Extract all professions
    let allProfs: Array<{ id: string; name: string; category_id?: string }> = [];
    if (opts.professions && opts.professions.length > 0) {
      allProfs = opts.professions;
    } else if (opts.categories) {
      allProfs = opts.categories.flatMap((c) =>
        (c.professions || []).map((p) => ({ ...p, category_id: c.id }))
      );
    }
    allProfs.sort((a, b) => a.name.localeCompare(b.name, "es"));

    if (onProfessionsLoaded) {
      onProfessionsLoaded(allProfs);
    }
  } catch (err) {
    console.warn("Could not load filter options:", err);
  }
}

async function executeSearch(container: HTMLElement, page: number, pageSize: number): Promise<void> {
  const grid = container.querySelector("#candidates-grid");
  const countEl = container.querySelector("#results-count");
  if (!grid) return;

  grid.innerHTML = `
    <div style="grid-column: 1 / -1; text-align: center; padding: 4rem; color: var(--text-muted);">
      <div class="spinner" style="margin-right: 0.5rem;"></div> Buscando candidatos...
    </div>
  `;

  const query = (container.querySelector("#search-query") as HTMLInputElement)?.value.trim();
  const categoryId = (container.querySelector("#facet-category") as HTMLSelectElement)?.value;
  const professionId = (container.querySelector("#facet-profession") as HTMLSelectElement)?.value;
  const academicLevel = (container.querySelector("#facet-level") as HTMLSelectElement)?.value;
  const department = (container.querySelector("#facet-department") as HTMLSelectElement)?.value;
  const minExpStr = (container.querySelector("#facet-min-exp") as HTMLInputElement)?.value;
  const minExp = minExpStr ? parseInt(minExpStr, 10) : undefined;
  const sort = (container.querySelector("#sort-select") as HTMLSelectElement)?.value;

  try {
    const res = await searchService.searchCandidates({
      q: query || undefined,
      category_id: categoryId || undefined,
      profession_id: professionId || undefined,
      academic_level: academicLevel || undefined,
      department: department || undefined,
      min_experience_years: minExp,
      page,
      page_size: pageSize,
      sort_by: sort === "exp_desc" ? "experience" : "name",
      sort_order: sort === "exp_desc" ? "desc" : "asc",
    });

    if (countEl) {
      countEl.innerHTML = `Se encontraron <strong>${res.total}</strong> candidato(s)`;
    }

    if (!res.items || res.items.length === 0) {
      grid.innerHTML = `
        <div style="grid-column: 1 / -1; text-align: center; padding: 3rem; color: var(--text-muted);">
          No se encontraron candidatos que coincidan con los criterios de búsqueda.
        </div>
      `;
      renderPagination("search-pagination", 1, 0, 0, () => {});
      return;
    }

    grid.innerHTML = res.items.map((c: CandidateItem) => {
      const docCount = c.document_count ?? c.documents_count ?? 1;
      const profName = c.profession_name || c.primary_profession || "Profesión no especificada";
      const catName = c.category_name || c.primary_category || "";
      const acadLevel = c.highest_academic_level || c.top_education || "No registrado";
      const expYears = c.total_experience_years !== null && c.total_experience_years !== undefined
        ? `${c.total_experience_years} años`
        : "Sin datos";

      return `
      <div class="card card-interactive" style="padding: 1.25rem; display: flex; flex-direction: column; justify-content: space-between; border: 1px solid var(--border-subtle); transition: all var(--transition-fast);">
        <div>
          <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 0.5rem;">
            <div style="font-weight: 700; color: var(--text-primary); font-size: 1rem; line-height: 1.3;">
              ${c.full_name}
            </div>
            <span class="badge" style="background: rgba(2, 132, 199, 0.15); color: #38BDF8; font-size: 0.7rem; font-weight: 600;">
              ${docCount} doc(s)
            </span>
          </div>

          <div style="font-size: 0.775rem; color: var(--text-muted); font-family: var(--font-mono); margin-bottom: 0.75rem;">
            ${c.identification_type || "CC"} ${c.identification_number || "No registrado"}
          </div>

          <div style="margin-bottom: 0.75rem;">
            <div style="font-size: 0.875rem; font-weight: 600; color: #38BDF8; margin-bottom: 0.2rem;">
              ${profName}
            </div>
            ${catName ? `<div style="font-size: 0.75rem; color: var(--text-muted);">${catName}</div>` : ""}
          </div>

          <div style="font-size: 0.8rem; color: var(--text-secondary); display: flex; flex-direction: column; gap: 0.25rem; margin-bottom: 1rem;">
            <div><strong>Nivel Académico:</strong> ${acadLevel}</div>
            <div><strong>Experiencia Total:</strong> ${expYears}</div>
            ${c.department ? `<div><strong>Ubicación:</strong> ${c.municipality ? `${c.municipality}, ` : ""}${c.department}</div>` : ""}
          </div>
        </div>

        <button class="btn btn-outline btn-sm btn-open-dossier" data-id="${c.id}" style="width: 100%; justify-content: center; font-weight: 600;">
          Ver Dossier Completo
        </button>
      </div>
    `;
    }).join("");

    // Wire Dossier Buttons
    grid.querySelectorAll(".btn-open-dossier").forEach((btn) => {
      btn.addEventListener("click", () => {
        const id = (btn as HTMLElement).dataset.id;
        if (id) openCandidateDossier(container, id);
      });
    });

    // Wire Pagination
    renderPagination(
      "search-pagination",
      res.page,
      res.total_pages,
      res.total,
      (newPage) => executeSearch(container, newPage, pageSize)
    );
  } catch (err: any) {
    grid.innerHTML = `
      <div style="grid-column: 1 / -1; text-align: center; padding: 2rem; color: var(--color-danger);">
        Error en búsqueda: ${err.message || "Fallo de conexión"}
      </div>
    `;
    Toast.error("Error al buscar candidatos");
  }
}

async function openCandidateDossier(container: HTMLElement, candidateId: string): Promise<void> {
  const modalBackdrop = container.querySelector("#dossier-modal-backdrop") as HTMLElement;
  const modalName = container.querySelector("#dossier-modal-name") as HTMLElement;
  const modalBody = container.querySelector("#dossier-modal-body") as HTMLElement;

  modalName.textContent = "Cargando perfil del candidato...";
  modalBody.innerHTML = `<div style="text-align: center; padding: 3rem;"><div class="spinner"></div></div>`;
  modalBackdrop.style.display = "flex";

  try {
    const detail: CandidateFullDetail = await searchService.getCandidateDetail(candidateId);
    modalName.textContent = detail.full_name;

    modalBody.innerHTML = `
      <!-- Candidate Overview Header -->
      <div style="padding: 1rem; background: var(--bg-surface-elevated); border-radius: var(--radius-sm); margin-bottom: 1.25rem;">
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 0.75rem; font-size: 0.85rem;">
          <div><strong>Identificación:</strong> ${detail.identification_type || "CC"} ${detail.identification_number || "No registrado"}</div>
          <div><strong>Nacionalidad:</strong> ${detail.nationality || "Colombiana"}</div>
          <div><strong>Sexo:</strong> ${detail.sex || "No especificado"}</div>
          <div><strong>Fecha Nacimiento:</strong> ${detail.birth_date || "No registrada"}</div>
          <div><strong>Profesión:</strong> ${detail.profession_name || "No especificada"}</div>
          <div><strong>Categoría:</strong> ${detail.category_name || "General"}</div>
        </div>
      </div>

      <!-- Contact Info -->
      ${detail.contact ? `
        <div style="margin-bottom: 1.25rem;">
          <h3 style="font-size: 0.95rem; font-weight: 700; color: #38BDF8; margin-bottom: 0.5rem;">Información de Contacto</h3>
          <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 0.5rem; font-size: 0.825rem; color: var(--text-secondary);">
            <div><strong>Email:</strong> ${detail.contact.email || "—"}</div>
            <div><strong>Celular:</strong> ${detail.contact.mobile_phone || "—"}</div>
            <div><strong>Ubicación:</strong> ${detail.contact.municipality || ""}, ${detail.contact.department || ""}</div>
            <div><strong>Dirección:</strong> ${detail.contact.address || "—"}</div>
          </div>
        </div>
      ` : ""}

      <!-- Work Experience -->
      <div style="margin-bottom: 1.25rem;">
        <h3 style="font-size: 0.95rem; font-weight: 700; color: #38BDF8; margin-bottom: 0.5rem;">Trayectoria Laboral</h3>
        ${detail.work_experiences && detail.work_experiences.length > 0 ? `
          <div style="display: flex; flex-direction: column; gap: 0.6rem;">
            ${detail.work_experiences.map((exp) => `
              <div style="padding: 0.65rem 0.85rem; background: var(--bg-surface-elevated); border-radius: 4px; font-size: 0.825rem;">
                <div style="font-weight: 600; color: var(--text-primary);">${exp.position} &bull; <span style="color: var(--text-secondary);">${exp.company_name}</span></div>
                <div style="font-size: 0.75rem; color: var(--text-muted); margin-top: 2px;">
                  ${exp.start_date || "—"} a ${exp.is_current ? "Presente" : (exp.end_date || "—")} (${exp.total_months || 0} meses)
                  ${exp.is_public_sector ? `<span class="badge" style="margin-left: 0.4rem; background: rgba(56, 189, 248, 0.15); color: #38BDF8; font-size: 0.65rem;">Sector Público</span>` : ""}
                </div>
              </div>
            `).join("")}
          </div>
        ` : `<div style="color: var(--text-muted); font-size: 0.8rem;">Sin registros laborales.</div>`}
      </div>

      <!-- Education -->
      <div style="margin-bottom: 1.25rem;">
        <h3 style="font-size: 0.95rem; font-weight: 700; color: #38BDF8; margin-bottom: 0.5rem;">Formación Académica</h3>
        ${detail.educations && detail.educations.length > 0 ? `
          <div style="display: flex; flex-direction: column; gap: 0.6rem;">
            ${detail.educations.map((edu) => `
              <div style="padding: 0.65rem 0.85rem; background: var(--bg-surface-elevated); border-radius: 4px; font-size: 0.825rem;">
                <div style="font-weight: 600; color: var(--text-primary);">${edu.degree_title}</div>
                <div style="font-size: 0.75rem; color: var(--text-muted); margin-top: 2px;">
                  ${edu.institution} &bull; ${edu.academic_level || ""} ${edu.graduation_date ? `(${edu.graduation_date})` : ""}
                </div>
              </div>
            `).join("")}
          </div>
        ` : `<div style="color: var(--text-muted); font-size: 0.8rem;">Sin registros académicos.</div>`}
      </div>

      <!-- Associated Documents -->
      <div>
        <h3 style="font-size: 0.95rem; font-weight: 700; color: #38BDF8; margin-bottom: 0.5rem;">Hojas de Vida Vinculadas</h3>
        <div style="display: flex; gap: 0.5rem; flex-wrap: wrap;">
          ${detail.documents && detail.documents.length > 0 ? detail.documents.map((doc) => `
            <a href="#/documents/${doc.id}" class="btn btn-outline btn-sm" style="font-size: 0.8rem;">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/></svg>
              ${doc.filename}
            </a>
          `).join("") : `<span style="color: var(--text-muted); font-size: 0.8rem;">No hay documentos registrados.</span>`}
        </div>
      </div>
    `;
  } catch (err: any) {
    modalBody.innerHTML = `<div style="color: var(--color-danger); padding: 2rem; text-align: center;">Error al cargar detalle del candidato.</div>`;
  }
}
