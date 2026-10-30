"use client";
// Typed fetch wrapper around the ComplyMate API. Adds the bearer token and tenant header, maps the
// error envelope to ApiError, and raises a "step-up" event when a sensitive action needs fresh MFA.
import { getTenantId, getToken } from "./auth";

export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  constructor(public status: number, public code: string, message: string, public details?: unknown) {
    super(message);
  }
}

type Options = {
  method?: string;
  body?: unknown;
  form?: FormData;
  headers?: Record<string, string>;
  tenant?: string | null;
};

async function headersFor(opts: Options): Promise<Record<string, string>> {
  const headers: Record<string, string> = { ...(opts.headers ?? {}) };
  const token = await getToken();
  if (token) headers.Authorization = `Bearer ${token}`;
  const tenant = opts.tenant === undefined ? getTenantId() : opts.tenant;
  if (tenant) headers["X-Tenant-Id"] = tenant;
  if (opts.body !== undefined) headers["Content-Type"] = "application/json";
  return headers;
}

async function raise(resp: Response): Promise<never> {
  let code = `http_${resp.status}`;
  let message = resp.statusText;
  let details: unknown;
  try {
    const data = await resp.json();
    code = data?.error?.code ?? code;
    message = data?.error?.message ?? message;
    details = data?.error?.details;
  } catch {
    /* non-JSON error */
  }
  if (resp.status === 401 && code === "step_up_mfa_required") {
    window.dispatchEvent(new CustomEvent("cm:step-up", { detail: { message } }));
  } else if (resp.status === 401 && typeof window !== "undefined" && !window.location.pathname.startsWith("/sign-in")) {
    window.location.href = "/sign-in";
  }
  throw new ApiError(resp.status, code, message, details);
}

export async function api<T = unknown>(path: string, opts: Options = {}): Promise<T> {
  const resp = await fetch(`${API_URL}${path}`, {
    method: opts.method ?? (opts.body !== undefined || opts.form ? "POST" : "GET"),
    headers: await headersFor(opts),
    body: opts.form ?? (opts.body !== undefined ? JSON.stringify(opts.body) : undefined),
  });
  if (!resp.ok) return raise(resp);
  if (resp.status === 204) return undefined as T;
  const type = resp.headers.get("content-type") ?? "";
  return (type.includes("application/json") ? resp.json() : resp.text()) as Promise<T>;
}

/** Downloads a file response (exports, certificates) and saves it in the browser. */
export async function download(path: string, fallbackName: string): Promise<void> {
  const resp = await fetch(`${API_URL}${path}`, { headers: await headersFor({}) });
  if (!resp.ok) return raise(resp);
  const disposition = resp.headers.get("content-disposition") ?? "";
  const match = /filename="?([^";]+)"?/.exec(disposition);
  const blob = await resp.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = match?.[1] ?? fallbackName;
  a.click();
  URL.revokeObjectURL(url);
}

export const get = <T,>(path: string) => api<T>(path);
export const post = <T,>(path: string, body?: unknown) => api<T>(path, { method: "POST", body: body ?? {} });
export const put = <T,>(path: string, body: unknown) => api<T>(path, { method: "PUT", body });
export const patch = <T,>(path: string, body: unknown) => api<T>(path, { method: "PATCH", body });
export const del = <T,>(path: string) => api<T>(path, { method: "DELETE" });
