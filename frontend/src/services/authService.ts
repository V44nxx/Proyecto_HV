import { api } from "./api";
import { authStore, UserProfile } from "../store/authStore";

export interface LoginResponse {
  access_token: string;
  refresh_token?: string;
  token_type: string;
  expires_at?: string;
  user?: {
    id: string;
    email: string;
    full_name: string;
    role: string;
  };
}

export const authService = {
  async login(username: string, password: string): Promise<UserProfile> {
    const tokenData = await api.post<LoginResponse>("/auth/login", {
      email: username,
      password: password,
    });
    authStore.setTokens(tokenData.access_token, tokenData.refresh_token);

    // Fetch user profile after authentication
    try {
      const user = await this.getCurrentUser();
      authStore.setUser(user);
      return user;
    } catch {
      if (tokenData.user) {
        const user: UserProfile = {
          id: tokenData.user.id,
          email: tokenData.user.email,
          fullName: tokenData.user.full_name,
          role: tokenData.user.role,
          permissions: [],
        };
        authStore.setUser(user);
        return user;
      }
      throw new Error("No se pudo cargar el perfil del usuario");
    }
  },

  async getCurrentUser(): Promise<UserProfile> {
    const data = await api.get<any>("/users/me");
    return {
      id: data.id,
      email: data.email,
      fullName: data.full_name || data.email,
      role: data.role,
      permissions: data.permissions || [],
    };
  },

  async logout(): Promise<void> {
    try {
      await api.post("/auth/logout");
    } catch {
      // Best-effort logout
    } finally {
      authStore.clear();
      window.location.hash = "#/login";
    }
  },
};
