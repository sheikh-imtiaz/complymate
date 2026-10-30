"use client";
import { getToken } from "./auth";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  constructor(public status: number, public code: string, message: string) {
    super(message);
  }
}

export async function api<T = unknown>(path: string, init: { method?: string; body?: unknown; headers?: Record<string, string> } = {}): Promise<T> {
  const token = await getToken();
  const resp = await fetch(`${API}${path}`, {
    method: init.method ?? (init.body !== undefined ? "POST" : "GET"),
    headers: {
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(init.body !== undefined ? { "Content-Type": "application/json" } : {}),
      ...(init.headers ?? {}),
    },
    body: init.body !== undefined ? JSON.stringify(init.body) : undefined,
  });
  if (!resp.ok) {
    const data = await resp.json().catch(() => ({}));
    const code = data?.error?.code ?? `http_${resp.status}`;
    if (resp.status === 401 && code !== "step_up_mfa_required") window.location.href = "/sign-in";
    if (code === "step_up_mfa_required") window.dispatchEvent(new CustomEvent("cm:step-up"));
    throw new ApiError(resp.status, code, data?.error?.message ?? resp.statusText);
  }
  return resp.json() as Promise<T>;
}

export const get = <T,>(p: string) => api<T>(p);
export const post = <T,>(p: string, body: unknown = {}) => api<T>(p, { method: "POST", body });
export const put = <T,>(p: string, body: unknown) => api<T>(p, { method: "PUT", body });
export const patch = <T,>(p: string, body: unknown) => api<T>(p, { method: "PATCH", body });
