import { api } from "./api";

export interface UserItem {
  id: string;
  email: string;
  full_name: string;
  role: string;
  is_active: boolean;
  created_at: string;
}

export interface UserListResponse {
  items: UserItem[];
  total: number;
  page: number;
  page_size: number;
}

export const userService = {
  async listUsers(params?: {
    page?: number;
    page_size?: number;
    role?: string;
    is_active?: boolean;
  }): Promise<UserListResponse> {
    return await api.get<UserListResponse>("/users", { params });
  },

  async createUser(payload: {
    email: string;
    full_name: string;
    role: string;
    password: string;
  }): Promise<UserItem> {
    return await api.post<UserItem>("/users", payload);
  },

  async updateUser(id: string, payload: { full_name?: string; role?: string }): Promise<UserItem> {
    return await api.put<UserItem>(`/users/${id}`, payload);
  },

  async deactivateUser(id: string): Promise<void> {
    await api.delete(`/users/${id}`);
  },
};
