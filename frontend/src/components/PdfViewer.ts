import * as pdfjsLib from "pdfjs-dist";

// Configure worker for Vite bundling
try {
  pdfjsLib.GlobalWorkerOptions.workerSrc = new URL(
    "pdfjs-dist/build/pdf.worker.min.mjs",
    import.meta.url
  ).toString();
} catch (e) {
  console.warn("Could not set pdf.workerSrc with import.meta.url, using unpkg fallback", e);
  pdfjsLib.GlobalWorkerOptions.workerSrc = "https://cdnjs.cloudflare.com/ajax/libs/pdf.js/4.4.168/pdf.worker.min.mjs";
}

export class PdfViewer {
  private container: HTMLElement;
  private pdfDoc: any = null;
  private currentPage: number = 1;
  private totalPages: number = 0;
  private currentScale: number = 1.25;
  private isRendering: boolean = false;
  private pendingPage: number | null = null;
  private pdfBlobUrl: string | null = null;

  constructor(container: HTMLElement) {
    this.container = container;
    this.renderShell();
  }

  private renderShell(): void {
    this.container.innerHTML = `
      <div class="pdf-viewer-wrapper" style="display: flex; flex-direction: column; height: 100%; width: 100%; background: #0F172A; border-radius: var(--radius-md); overflow: hidden; border: 1px solid var(--border-subtle);">
        <!-- Toolbar -->
        <div class="pdf-toolbar" style="
          display: flex;
          align-items: center;
          justify-content: space-between;
          padding: 0.5rem 1rem;
          background: #1E293B;
          border-bottom: 1px solid #334155;
          color: #F8FAFC;
          font-size: 0.825rem;
          flex-shrink: 0;
          z-index: 10;
        ">
          <!-- Page navigation -->
          <div style="display: flex; align-items: center; gap: 0.5rem;">
            <button id="pdf-btn-prev" class="btn btn-outline btn-sm" style="padding: 0.25rem 0.6rem; color: #FFF; border-color: #475569;" title="Página anterior">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="15 18 9 12 15 6"/></svg>
            </button>
            <div style="display: flex; align-items: center; gap: 0.25rem;">
              <span>Pág.</span>
              <input id="pdf-input-page" type="number" min="1" max="1" value="1" style="
                width: 44px;
                padding: 0.2rem 0.35rem;
                background: #0F172A;
                border: 1px solid #475569;
                border-radius: 4px;
                color: #FFF;
                text-align: center;
                font-size: 0.8rem;
              "/>
              <span>de <strong id="pdf-total-pages">0</strong></span>
            </div>
            <button id="pdf-btn-next" class="btn btn-outline btn-sm" style="padding: 0.25rem 0.6rem; color: #FFF; border-color: #475569;" title="Página siguiente">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="9 18 15 12 9 6"/></svg>
            </button>
          </div>

          <!-- Traceability banner / badge -->
          <div id="pdf-trace-badge" style="
            display: inline-flex;
            align-items: center;
            gap: 0.35rem;
            font-size: 0.725rem;
            font-weight: 600;
            padding: 0.2rem 0.5rem;
            border-radius: 4px;
            background: rgba(2, 132, 199, 0.2);
            color: #38BDF8;
            border: 1px solid rgba(56, 189, 248, 0.3);
          ">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
            <span>Trazabilidad Activa</span>
          </div>

          <!-- Zoom controls -->
          <div style="display: flex; align-items: center; gap: 0.4rem;">
            <button id="pdf-btn-zoom-out" class="btn btn-outline btn-sm" style="padding: 0.25rem 0.5rem; color: #FFF; border-color: #475569;" title="Reducir zoom">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="5" y1="12" x2="19" y2="12"/></svg>
            </button>
            <span id="pdf-zoom-pct" style="min-width: 44px; text-align: center; font-size: 0.75rem; color: #94A3B8;">125%</span>
            <button id="pdf-btn-zoom-in" class="btn btn-outline btn-sm" style="padding: 0.25rem 0.5rem; color: #FFF; border-color: #475569;" title="Aumentar zoom">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
            </button>
            <button id="pdf-btn-fit" class="btn btn-outline btn-sm" style="padding: 0.25rem 0.5rem; color: #FFF; border-color: #475569; font-size: 0.75rem;" title="Ajustar ancho">
              Ajustar
            </button>
          </div>
        </div>

        <!-- Canvas Stage -->
        <div id="pdf-canvas-container" style="
          flex: 1;
          overflow: auto;
          display: flex;
          align-items: flex-start;
          justify-content: center;
          padding: 1.5rem;
          background: #0B1120;
          position: relative;
        ">
          <div id="pdf-loading-indicator" style="display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 0.75rem; color: #94A3B8; margin-top: 3rem;">
            <div class="spinner"></div>
            <span>Cargando visor de documento PDF...</span>
          </div>
          <div id="pdf-canvas-wrapper" style="position: relative; display: none; box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.6); border-radius: 2px;">
            <canvas id="pdf-render-canvas" style="display: block;"></canvas>
            <div id="pdf-highlight-overlay" style="position: absolute; top: 0; left: 0; right: 0; bottom: 0; pointer-events: none; border: 2px solid transparent; transition: border-color 0.4s ease;"></div>
          </div>
        </div>
      </div>
    `;

    this.attachEventListeners();
  }

  private attachEventListeners(): void {
    const btnPrev = this.container.querySelector("#pdf-btn-prev") as HTMLButtonElement;
    const btnNext = this.container.querySelector("#pdf-btn-next") as HTMLButtonElement;
    const inputPage = this.container.querySelector("#pdf-input-page") as HTMLInputElement;
    const btnZoomIn = this.container.querySelector("#pdf-btn-zoom-in") as HTMLButtonElement;
    const btnZoomOut = this.container.querySelector("#pdf-btn-zoom-out") as HTMLButtonElement;
    const btnFit = this.container.querySelector("#pdf-btn-fit") as HTMLButtonElement;

    btnPrev?.addEventListener("click", () => {
      if (this.currentPage > 1) {
        this.goToPage(this.currentPage - 1);
      }
    });

    btnNext?.addEventListener("click", () => {
      if (this.currentPage < this.totalPages) {
        this.goToPage(this.currentPage + 1);
      }
    });

    inputPage?.addEventListener("change", () => {
      const pageNum = parseInt(inputPage.value, 10);
      if (pageNum >= 1 && pageNum <= this.totalPages) {
        this.goToPage(pageNum);
      } else {
        inputPage.value = this.currentPage.toString();
      }
    });

    btnZoomIn?.addEventListener("click", () => {
      this.currentScale = Math.min(3.0, this.currentScale + 0.25);
      this.updateZoomDisplay();
      this.renderCurrentPage();
    });

    btnZoomOut?.addEventListener("click", () => {
      this.currentScale = Math.max(0.5, this.currentScale - 0.25);
      this.updateZoomDisplay();
      this.renderCurrentPage();
    });

    btnFit?.addEventListener("click", () => {
      const viewportWidth = this.container.querySelector("#pdf-canvas-container")?.clientWidth || 800;
      this.currentScale = Math.max(0.6, Math.min(2.0, (viewportWidth - 64) / 600));
      this.updateZoomDisplay();
      this.renderCurrentPage();
    });
  }

  private updateZoomDisplay(): void {
    const zoomPctEl = this.container.querySelector("#pdf-zoom-pct");
    if (zoomPctEl) {
      zoomPctEl.textContent = `${Math.round(this.currentScale * 100)}%`;
    }
  }

  public async loadFromBlob(blob: Blob): Promise<void> {
    try {
      if (this.pdfBlobUrl) {
        URL.revokeObjectURL(this.pdfBlobUrl);
      }
      this.pdfBlobUrl = URL.createObjectURL(blob);
      const arrayBuffer = await blob.arrayBuffer();
      await this.loadFromArrayBuffer(arrayBuffer);
    } catch (err) {
      console.error("Error loading PDF from blob:", err);
      this.showError("No fue posible cargar el archivo PDF.");
    }
  }

  public async loadFromArrayBuffer(data: ArrayBuffer): Promise<void> {
    const loadingEl = this.container.querySelector("#pdf-loading-indicator") as HTMLElement;
    if (loadingEl) loadingEl.style.display = "flex";

    try {
      const loadingTask = pdfjsLib.getDocument({ data });
      this.pdfDoc = await loadingTask.promise;
      this.totalPages = this.pdfDoc.numPages;

      const totalEl = this.container.querySelector("#pdf-total-pages");
      if (totalEl) totalEl.textContent = this.totalPages.toString();

      const inputPage = this.container.querySelector("#pdf-input-page") as HTMLInputElement;
      if (inputPage) inputPage.max = this.totalPages.toString();

      this.currentPage = 1;
      await this.renderCurrentPage();
    } catch (err) {
      console.error("Failed to parse PDF document:", err);
      this.showError("El documento no se pudo procesar como PDF válido.");
    }
  }

  public async goToPage(pageNumber: number): Promise<void> {
    if (!this.pdfDoc || pageNumber < 1 || pageNumber > this.totalPages) return;

    this.currentPage = pageNumber;
    const inputPage = this.container.querySelector("#pdf-input-page") as HTMLInputElement;
    if (inputPage) inputPage.value = pageNumber.toString();

    // Visual pulse on traceability jump
    const overlay = this.container.querySelector("#pdf-highlight-overlay") as HTMLElement;
    if (overlay) {
      overlay.style.borderColor = "#38BDF8";
      setTimeout(() => {
        overlay.style.borderColor = "transparent";
      }, 1200);
    }

    if (this.isRendering) {
      this.pendingPage = pageNumber;
    } else {
      await this.renderCurrentPage();
    }

    // Scroll canvas container to top for fresh page view
    const canvasContainer = this.container.querySelector("#pdf-canvas-container");
    if (canvasContainer) {
      canvasContainer.scrollTop = 0;
    }
  }

  public getCurrentPage(): number {
    return this.currentPage;
  }

  public getTotalPages(): number {
    return this.totalPages;
  }

  private async renderCurrentPage(): Promise<void> {
    if (!this.pdfDoc) return;
    this.isRendering = true;

    const loadingEl = this.container.querySelector("#pdf-loading-indicator") as HTMLElement;
    const canvasWrapper = this.container.querySelector("#pdf-canvas-wrapper") as HTMLElement;
    const canvas = this.container.querySelector("#pdf-render-canvas") as HTMLCanvasElement;

    try {
      const page = await this.pdfDoc.getPage(this.currentPage);
      const viewport = page.getViewport({ scale: this.currentScale });

      const context = canvas.getContext("2d");
      if (!context) throw new Error("Could not acquire 2D context");

      canvas.height = viewport.height;
      canvas.width = viewport.width;

      const renderContext = {
        canvasContext: context,
        viewport: viewport,
      };

      await page.render(renderContext).promise;

      if (loadingEl) loadingEl.style.display = "none";
      if (canvasWrapper) canvasWrapper.style.display = "block";
    } catch (err) {
      console.error("Error rendering PDF page:", err);
    } finally {
      this.isRendering = false;
      if (this.pendingPage !== null) {
        const next = this.pendingPage;
        this.pendingPage = null;
        await this.goToPage(next);
      }
    }
  }

  private showError(msg: string): void {
    const loadingEl = this.container.querySelector("#pdf-loading-indicator");
    if (loadingEl) {
      loadingEl.innerHTML = `
        <div style="color: var(--color-danger); text-align: center; padding: 2rem;">
          <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="margin-bottom: 0.5rem;"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
          <div style="font-weight: 600;">${msg}</div>
        </div>
      `;
    }
  }

  public destroy(): void {
    if (this.pdfBlobUrl) {
      URL.revokeObjectURL(this.pdfBlobUrl);
      this.pdfBlobUrl = null;
    }
    this.pdfDoc = null;
  }
}
