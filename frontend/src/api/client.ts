import axios from "axios";

// The Anthropic API key never lives here. Only the backend talks to Claude.
export const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL ?? "http://localhost:8000",
});

// Attach the token to every request.
api.interceptors.request.use((config) => {
  const token = localStorage.getItem("medlens_token");
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

// An expired or invalid token clears the session and returns to login.
api.interceptors.response.use(
  (response) => response,
  (error) => {
    const status = error?.response?.status;
    const isAuthCall = error?.config?.url?.includes("/api/auth/");
    if (status === 401 && !isAuthCall) {
      localStorage.removeItem("medlens_token");
      if (window.location.pathname !== "/login") {
        window.location.href = "/login";
      }
    }
    return Promise.reject(error);
  }
);
