/**
 * Proyecto HV — Centralized HTTP Client
 * Handles base URL, auth token injection, automatic 401 refresh, and error formatting.
 */

import { authStore } from "../store/authStore";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "/api/v1";

interface RequestOptions extends RequestInit {
  params?: Record<string, string | number | boolean | undefined | null>;
}

export class ApiError extends Error {
  public status: number;
  public data: any;

  constructor(message: string, status: number, data?: any) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.data = data;
  }
}

let isRefreshing = false;
let refreshSubscribers: Array<(token: string) => void> = [];

function onRefreshed(token: string) {
  refreshSubscribers.forEach((cb) => cb(token));
  refreshSubscribers = [];
}

async function request<T = any>(endpoint: string, options: RequestOptions = {}): Promise<T> {
  const { params, headers, ...customConfig } = options;

  let url = endpoint.startsWith("http") ? endpoint : `${API_BASE_URL}${endpoint.startsWith("/") ? "" : "/"}${endpoint}`;

  if (params) {
    const queryParams = new URLSearchParams();
    for (const [key, value] of Object.entries(params)) {
      if (value !== undefined && value !== null && value !== "") {
        queryParams.append(key, String(value));
      }
    }
    const queryString = queryParams.toString();
    if (queryString) {
      url += (url.includes("?") ? "&" : "?") + queryString;
    }
  }

  const reqHeaders: Record<string, string> = {
    Accept: "application/json",
    ...((headers as Record<string, string>) || {}),
  };

  const token = authStore.getAccessToken();
  if (token && !reqHeaders.Authorization) {
    reqHeaders.Authorization = `Bearer ${token}`;
  }

  if (!(customConfig.body instanceof FormData) && !reqHeaders["Content-Type"]) {
    reqHeaders["Content-Type"] = "application/json";
  }

  const response = await fetch(url, {
    ...customConfig,
    headers: reqHeaders,
  });

  // Handle HTTP 401 Unauthorized (attempt token refresh)
  if (response.status === 401 && !endpoint.includes("/auth/login") && !endpoint.includes("/auth/refresh")) {
    const refreshToken = authStore.getRefreshToken();
    if (!refreshToken) {
      authStore.clear();
      window.location.hash = "#/login";
      throw new ApiError("Sesión expirada. Por favor inicie sesión nuevamente.", 401);
    }

    if (!isRefreshing) {
      isRefreshing = true;
      try {
        const refreshResponse = await fetch(`${API_BASE_URL}/auth/refresh`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ refresh_token: refreshToken }),
        });

        if (refreshResponse.ok) {
          const refreshData = await refreshResponse.json();
          authStore.setTokens(refreshData.access_token, refreshData.refresh_token);
          onRefreshed(refreshData.access_token);
        } else {
          authStore.clear();
          window.location.hash = "#/login";
          throw new ApiError("Sesión expirada. Por favor inicie sesión nuevamente.", 401);
        }
      } catch (err) {
        authStore.clear();
        window.location.hash = "#/login";
        throw err;
      } finally {
        isRefreshing = false;
      }
    }

    return new Promise((resolve) => {
      refreshSubscribers.push((newToken: string) => {
        reqHeaders.Authorization = `Bearer ${newToken}`;
        resolve(request<T>(endpoint, { ...options, headers: reqHeaders }));
      });
    });
  }

  // Handle Error Responses
  if (!response.ok) {
    let errorDetail = `Error ${response.status}: ${response.statusText}`;
    let responseData: any = null;

    try {
      const contentType = response.headers.get("content-type");
      if (contentType && contentType.includes("application/json")) {
        responseData = await response.json();
        if (responseData.detail) {
          if (typeof responseData.detail === "string") {
            errorDetail = responseData.detail;
          } else if (typeof responseData.detail === "object") {
            errorDetail = responseData.detail.message || JSON.stringify(responseData.detail);
          }
        } else if (responseData.message) {
          errorDetail = responseData.message;
        }
      } else {
        const text = await response.text();
        if (text) errorDetail = text;
      }
    } catch {
      // Ignore json parse error on error response
    }

    throw new ApiError(errorDetail, response.status, responseData);
  }

  // Handle Successful Responses
  if (response.status === 204) {
    return {} as T;
  }

  const contentType = response.headers.get("content-type");
  if (contentType && contentType.includes("application/json")) {
    return (await response.json()) as T;
  }

  return (await response.blob()) as unknown as T;
}

export const api = {
  get: <T = any>(endpoint: string, options?: RequestOptions) =>
    request<T>(endpoint, { ...options, method: "GET" }),

  post: <T = any>(endpoint: string, body?: any, options?: RequestOptions) =>
    request<T>(endpoint, {
      ...options,
      method: "POST",
      body: body instanceof FormData ? body : JSON.stringify(body),
    }),

  put: <T = any>(endpoint: string, body?: any, options?: RequestOptions) =>
    request<T>(endpoint, {
      ...options,
      method: "PUT",
      body: body instanceof FormData ? body : JSON.stringify(body),
    }),

  delete: <T = any>(endpoint: string, options?: RequestOptions) =>
    request<T>(endpoint, { ...options, method: "DELETE" }),
};
