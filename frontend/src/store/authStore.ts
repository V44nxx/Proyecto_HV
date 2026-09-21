/**
 * Proyecto HV — Central Authentication & RBAC Store
 * Manages JWT tokens, current user profile, and permission checks.
 */

export interface UserProfile {
  id: string;
  email: string;
  fullName: string;
  role: "ADMIN" | "GESTOR" | "REVISOR" | "CONSULTOR" | string;
  permissions: string[];
}

class AuthStore {
  private user: UserProfile | null = null;
  private listeners: Array<() => void> = [];

  constructor() {
    this.loadFromStorage();
  }

  private loadFromStorage(): void {
    try {
      const stored = localStorage.getItem("hv_user");
      if (stored) {
        this.user = JSON.parse(stored);
      }
    } catch {
      this.user = null;
    }
  }

  public getAccessToken(): string | null {
    return localStorage.getItem("hv_access_token");
  }

  public getRefreshToken(): string | null {
    return localStorage.getItem("hv_refresh_token");
  }

  public setTokens(accessToken: string, refreshToken?: string): void {
    localStorage.setItem("hv_access_token", accessToken);
    if (refreshToken) {
      localStorage.setItem("hv_refresh_token", refreshToken);
    }
  }

  public getUser(): UserProfile | null {
    return this.user;
  }

  public setUser(user: UserProfile | null): void {
    this.user = user;
    if (user) {
      localStorage.setItem("hv_user", JSON.stringify(user));
    } else {
      localStorage.removeItem("hv_user");
    }
    this.notify();
  }

  public isAuthenticated(): boolean {
    return !!this.getAccessToken() && !!this.user;
  }

  public hasPermission(permission: string): boolean {
    if (!this.user) return false;
    if (this.user.role === "ADMIN") return true;
    return this.user.permissions?.includes(permission) || false;
  }

  public hasRole(role: string): boolean {
    return this.user?.role === role;
  }

  public clear(): void {
    this.user = null;
    localStorage.removeItem("hv_access_token");
    localStorage.removeItem("hv_refresh_token");
    localStorage.removeItem("hv_user");
    this.notify();
  }

  public subscribe(listener: () => void): () => void {
    this.listeners.push(listener);
    return () => {
      this.listeners = this.listeners.filter((l) => l !== listener);
    };
  }

  private notify(): void {
    for (const listener of this.listeners) {
      listener();
    }
  }
}

export const authStore = new AuthStore();
