import { authStore } from "../store/authStore";

export function renderSidebar(currentPath: string = ""): string {
  const canManageUsers = authStore.hasRole("ADMIN") || authStore.hasPermission("users:read");

  const navItems = [
    {
      label: "Inicio",
      href: "#/dashboard",
      path: "/dashboard",
      icon: `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/></svg>`,
    },
    {
      label: "Hojas de vida",
      href: "#/documents",
      path: "/documents",
      icon: `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/></svg>`,
    },
    {
      label: "Búsqueda",
      href: "#/search",
      path: "/search",
      icon: `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>`,
    },
    {
      label: "Revisión Humana",
      href: "#/reviews",
      path: "/reviews",
      icon: `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M9 11l3 3L22 4"/><path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"/></svg>`,
    },
    {
      label: "Reportes",
      href: "#/reports",
      path: "/reports",
      icon: `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21.21 15.89A10 10 0 1 1 8 2.83"/><path d="M22 12A10 10 0 0 0 12 2v10z"/></svg>`,
    },
  ];

  if (canManageUsers) {
    navItems.push({
      label: "Usuarios",
      href: "#/users",
      path: "/users",
      icon: `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>`,
    });
  }

  const itemsHtml = navItems
    .map((item) => {
      const isActive = currentPath.startsWith(item.path);
      return `
        <a href="${item.href}" class="nav-item ${isActive ? "active" : ""}" style="
          display: flex;
          align-items: center;
          gap: 0.75rem;
          padding: 0.75rem 1rem;
          margin-bottom: 0.25rem;
          color: ${isActive ? "#38BDF8" : "var(--text-secondary)"};
          background: ${isActive ? "rgba(56, 189, 248, 0.08)" : "transparent"};
          border-left: 3px solid ${isActive ? "#38BDF8" : "transparent"};
          border-radius: 0 var(--radius-sm) var(--radius-sm) 0;
          font-weight: ${isActive ? "600" : "500"};
          font-size: 0.875rem;
          text-decoration: none;
          transition: all var(--transition-fast);
        ">
          ${item.icon}
          <span>${item.label}</span>
        </a>
      `;
    })
    .join("");

  return `
    <aside class="sidebar" style="
      width: var(--sidebar-width);
      background-color: var(--bg-sidebar);
      border-right: 1px solid var(--border-subtle);
      display: flex;
      flex-direction: column;
      flex-shrink: 0;
      padding: 1.5rem 0.5rem;
    ">
      <div style="padding: 0 0.75rem 1.25rem; border-bottom: 1px solid var(--border-subtle); margin-bottom: 1rem;">
        <span style="font-size: 0.7rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.08em; color: var(--text-muted);">
          Navegación Principal
        </span>
      </div>
      <nav style="flex: 1;">
        ${itemsHtml}
      </nav>
      <div style="padding: 1rem 0.75rem; border-top: 1px solid var(--border-subtle); font-size: 0.75rem; color: var(--text-muted);">
        Versión 1.0.0 (Prod)
      </div>
    </aside>
  `;
}
