/**
 * Proyecto HV — Toast Notifications
 * Non-intrusive alert messages for asynchronous user operations.
 */

export class Toast {
  private static container: HTMLElement | null = null;

  private static ensureContainer(): HTMLElement {
    if (!this.container) {
      this.container = document.createElement("div");
      this.container.className = "toast-container";
      document.body.appendChild(this.container);
    }
    return this.container;
  }

  public static show(message: string, type: "success" | "error" | "info" = "info", durationMs: number = 4000): void {
    const container = this.ensureContainer();

    const toast = document.createElement("div");
    toast.className = `toast ${type}`;

    const icon =
      type === "success"
        ? `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#34D399" stroke-width="2" stroke-linecap="round"><polyline points="20 6 9 17 4 12"/></svg>`
        : type === "error"
        ? `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#F87171" stroke-width="2" stroke-linecap="round"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>`
        : `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#60A5FA" stroke-width="2" stroke-linecap="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg>`;

    toast.innerHTML = `
      <div style="display: flex; align-items: center; gap: 0.6rem;">
        ${icon}
        <span style="font-size: 0.875rem; font-weight: 500;">${this.escapeHtml(message)}</span>
      </div>
      <button style="background: none; border: none; color: var(--text-muted); cursor: pointer; padding: 2px;" title="Cerrar">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
      </button>
    `;

    const closeBtn = toast.querySelector("button");
    closeBtn?.addEventListener("click", () => {
      toast.remove();
    });

    container.appendChild(toast);

    setTimeout(() => {
      if (toast.parentElement) {
        toast.style.opacity = "0";
        toast.style.transform = "translateX(50px)";
        toast.style.transition = "all 200ms ease";
        setTimeout(() => toast.remove(), 200);
      }
    }, durationMs);
  }

  public static success(message: string, durationMs?: number): void {
    this.show(message, "success", durationMs);
  }

  public static error(message: string, durationMs?: number): void {
    this.show(message, "error", durationMs || 5000);
  }

  public static info(message: string, durationMs?: number): void {
    this.show(message, "info", durationMs);
  }

  private static escapeHtml(text: string): string {
    const div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
  }
}
