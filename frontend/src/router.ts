import { authStore } from "./store/authStore";
import { renderNavbar, initNavbarEvents } from "./components/Navbar";
import { renderSidebar } from "./components/Sidebar";

// Page imports
import { renderLoginPage } from "./pages/LoginPage";
import { renderDashboardPage } from "./pages/DashboardPage";
import { renderDocumentsPage } from "./pages/DocumentsPage";
import { renderDocumentDetailPage } from "./pages/DocumentDetailPage";
import { renderSearchPage } from "./pages/SearchPage";
import { renderReviewsPage } from "./pages/ReviewsPage";
import { renderReportsPage } from "./pages/ReportsPage";
import { renderUsersPage } from "./pages/UsersPage";

export class Router {
  private appContainer: HTMLElement;
  private currentLayout: "auth" | "app" | null = null;

  constructor(appContainer: HTMLElement) {
    this.appContainer = appContainer;
  }

  public init(): void {
    window.addEventListener("hashchange", () => this.handleRoute());
    this.handleRoute();
  }

  private handleRoute(): void {
    const rawHash = window.location.hash || "#/";
    const path = rawHash.replace(/^#/, "") || "/";

    // Authentication Guard
    const isAuthenticated = authStore.isAuthenticated();

    if (!isAuthenticated && path !== "/login") {
      window.location.hash = "#/login";
      return;
    }

    if (isAuthenticated && (path === "/" || path === "/login")) {
      window.location.hash = "#/dashboard";
      return;
    }

    // Route matching
    if (path === "/login") {
      this.setLayout("auth");
      renderLoginPage(this.appContainer);
      return;
    }

    // Authenticated application layout
    this.setLayout("app", path);
    const mainEl = document.getElementById("main-content") as HTMLElement;
    if (!mainEl) return;

    // Clean previous content
    mainEl.innerHTML = "";

    // Match routes
    if (path === "/dashboard") {
      renderDashboardPage(mainEl);
    } else if (path === "/documents") {
      renderDocumentsPage(mainEl);
    } else if (path.startsWith("/documents/")) {
      const docId = path.split("/")[2];
      if (docId) {
        renderDocumentDetailPage(mainEl, docId);
      } else {
        window.location.hash = "#/documents";
      }
    } else if (path === "/search") {
      renderSearchPage(mainEl);
    } else if (path === "/reviews") {
      renderReviewsPage(mainEl);
    } else if (path === "/reports") {
      renderReportsPage(mainEl);
    } else if (path === "/users") {
      if (authStore.hasRole("ADMIN") || authStore.hasPermission("users:read")) {
        renderUsersPage(mainEl);
      } else {
        window.location.hash = "#/dashboard";
      }
    } else {
      // Default fallback
      window.location.hash = "#/dashboard";
    }
  }

  private setLayout(layout: "auth" | "app", currentPath: string = ""): void {
    if (this.currentLayout === layout && layout === "app") {
      // Just update sidebar active state
      const sidebarContainer = document.getElementById("sidebar-container");
      if (sidebarContainer) {
        sidebarContainer.innerHTML = renderSidebar(currentPath);
      }
      return;
    }

    this.currentLayout = layout;

    if (layout === "auth") {
      this.appContainer.innerHTML = "";
    } else {
      this.appContainer.innerHTML = `
        <div style="display: flex; flex-direction: column; min-height: 100vh; width: 100%; background: var(--bg-body);">
          ${renderNavbar()}
          <div style="display: flex; flex: 1; min-height: 0;">
            <div id="sidebar-container">${renderSidebar(currentPath)}</div>
            <main id="main-content" style="flex: 1; overflow-y: auto; min-height: 0;"></main>
          </div>
        </div>
      `;
      initNavbarEvents();
    }
  }
}
