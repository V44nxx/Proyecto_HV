import { api } from "./api";
import { authStore, UserProfile } from "../store/authStore";

export interface LoginResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

export const authService = {
  async login(username: string, password: string): Promise<UserProfile> {
    const formData = new FormData();
    formData.append("username", username);
    formData.append("password", password);

    const tokenData = await api.post<LoginResponse>("/auth/login", formData);
    authStore.setTokens(tokenData.access_token, tokenData.refresh_token);

    // Fetch user profile after authentication
    const user = await this.getCurrentUser();
    authStore.setUser(user);
    return user;
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
