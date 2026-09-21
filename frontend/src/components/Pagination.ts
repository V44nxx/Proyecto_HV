export interface PaginationProps {
  page: number;
  pageSize: number;
  total: number;
  totalPages: number;
  onPageChange: (newPage: number) => void;
}

export function renderPagination(
  containerId: string,
  page: number,
  totalPages: number,
  total: number,
  onPageChange: (newPage: number) => void
): void {
  const container = document.getElementById(containerId);
  if (!container) return;

  if (totalPages <= 1 && total <= 0) {
    container.innerHTML = "";
    return;
  }

  const prevDisabled = page <= 1 ? "disabled" : "";
  const nextDisabled = page >= totalPages ? "disabled" : "";

  container.innerHTML = `
    <div style="display: flex; align-items: center; justify-content: space-between; width: 100%; padding: 0.75rem 0; font-size: 0.85rem; color: var(--text-secondary);">
      <div>
        Mostrando página <strong>${page}</strong> de <strong>${Math.max(1, totalPages)}</strong> (${total} registros en total)
      </div>
      <div style="display: flex; gap: 0.5rem; align-items: center;">
        <button id="${containerId}-btn-prev" class="btn btn-outline btn-sm" ${prevDisabled}>
          &larr; Anterior
        </button>
        <span style="padding: 0 0.5rem; font-weight: 600; color: var(--text-primary);">${page}</span>
        <button id="${containerId}-btn-next" class="btn btn-outline btn-sm" ${nextDisabled}>
          Siguiente &rarr;
        </button>
      </div>
    </div>
  `;

  const btnPrev = document.getElementById(`${containerId}-btn-prev`);
  const btnNext = document.getElementById(`${containerId}-btn-next`);

  if (btnPrev && page > 1) {
    btnPrev.addEventListener("click", () => onPageChange(page - 1));
  }
  if (btnNext && page < totalPages) {
    btnNext.addEventListener("click", () => onPageChange(page + 1));
  }
}
