"use client";
// Authentication for the tenant app. Two modes:
//   dev  — local stack: POST /auth/dev-login with an email (no password), token kept in sessionStorage.
//   oidc — Cognito (AWS) or Entra External ID (Azure) via oidc-client-ts (authorization code + PKCE).
// The API receives the ID token (it carries the email claim) as a Bearer token.
import { UserManager, WebStorageStateStore, type User } from "oidc-client-ts";

const MODE = process.env.NEXT_PUBLIC_AUTH_MODE ?? "dev";
const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const TOKEN_KEY = "cm_token";
const TENANT_KEY = "cm_tenant";

let manager: UserManager | null = null;

function userManager(): UserManager {
  if (manager) return manager;
  const origin = window.location.origin;
  manager = new UserManager({
    authority: process.env.NEXT_PUBLIC_OIDC_ISSUER ?? "",
    client_id: process.env.NEXT_PUBLIC_OIDC_CLIENT_ID ?? "",
    redirect_uri: `${origin}/callback`,
    post_logout_redirect_uri: `${origin}/sign-in`,
    response_type: "code",
    scope: "openid email profile",
    userStore: new WebStorageStateStore({ store: window.sessionStorage }),
    automaticSilentRenew: true,
  });
  return manager;
}

export const authMode = MODE;

export async function getToken(): Promise<string | null> {
  if (typeof window === "undefined") return null;
  if (MODE === "oidc") {
    const user: User | null = await userManager().getUser();
    if (!user || user.expired) return null;
    return user.id_token ?? user.access_token;
  }
  return window.sessionStorage.getItem(TOKEN_KEY);
}

export async function signIn(email?: string): Promise<void> {
  if (MODE === "oidc") {
    await userManager().signinRedirect();
    return;
  }
  if (!email) throw new Error("email required in dev mode");
  const resp = await fetch(`${API}/auth/dev-login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email }),
  });
  if (!resp.ok) throw new Error("Sign-in failed");
  const data = (await resp.json()) as { access_token: string };
  window.sessionStorage.setItem(TOKEN_KEY, data.access_token);
  window.sessionStorage.setItem("cm_dev_email", email);
}

/** Completes the OIDC redirect on /callback. */
export async function completeSignIn(): Promise<void> {
  if (MODE === "oidc") await userManager().signinRedirectCallback();
}

/** Step-up MFA: re-authenticate so auth_time is fresh (sensitive actions need MFA in the last 10 minutes). */
export async function stepUp(): Promise<void> {
  if (MODE === "oidc") {
    sessionStorage.setItem("cm_return_to", window.location.pathname + window.location.search);
    await userManager().signinRedirect({ prompt: "login", extraQueryParams: { max_age: "0" } });
    return;
  }
  const email = window.sessionStorage.getItem("cm_dev_email");
  if (email) await signIn(email);
}

export async function signOut(): Promise<void> {
  window.localStorage.removeItem(TENANT_KEY);
  window.sessionStorage.removeItem(TOKEN_KEY);
  if (MODE === "oidc") {
    const um = userManager();
    await um.removeUser();
    const domain = process.env.NEXT_PUBLIC_OIDC_DOMAIN;
    if (domain) {
      const params = new URLSearchParams({
        client_id: process.env.NEXT_PUBLIC_OIDC_CLIENT_ID ?? "",
        logout_uri: `${window.location.origin}/sign-in`,
      });
      window.location.href = `${domain}/logout?${params.toString()}`;
      return;
    }
  }
  window.location.href = "/sign-in";
}

export function getTenantId(): string | null {
  return typeof window === "undefined" ? null : window.localStorage.getItem(TENANT_KEY);
}

export function setTenantId(id: string | null): void {
  if (id) window.localStorage.setItem(TENANT_KEY, id);
  else window.localStorage.removeItem(TENANT_KEY);
}
