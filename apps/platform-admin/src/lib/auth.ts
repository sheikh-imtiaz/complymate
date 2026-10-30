"use client";
// Platform admin uses its own app client (shorter sessions). Same OIDC provider as the tenant app.
import { UserManager, WebStorageStateStore } from "oidc-client-ts";

const MODE = process.env.NEXT_PUBLIC_AUTH_MODE ?? "dev";
const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
let manager: UserManager | null = null;

function um(): UserManager {
  manager ??= new UserManager({
    authority: process.env.NEXT_PUBLIC_OIDC_ISSUER ?? "",
    client_id: process.env.NEXT_PUBLIC_OIDC_CLIENT_ID ?? "",
    redirect_uri: `${window.location.origin}/callback`,
    response_type: "code",
    scope: "openid email profile",
    userStore: new WebStorageStateStore({ store: window.sessionStorage }),
  });
  return manager;
}

export const authMode = MODE;

export async function getToken(): Promise<string | null> {
  if (typeof window === "undefined") return null;
  if (MODE === "oidc") {
    const user = await um().getUser();
    return user && !user.expired ? (user.id_token ?? null) : null;
  }
  return sessionStorage.getItem("cm_admin_token");
}

export async function signIn(email?: string): Promise<void> {
  if (MODE === "oidc") return um().signinRedirect();
  const resp = await fetch(`${API}/auth/dev-login`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ email }) });
  if (!resp.ok) throw new Error("Sign-in failed");
  sessionStorage.setItem("cm_admin_token", ((await resp.json()) as { access_token: string }).access_token);
  sessionStorage.setItem("cm_admin_email", email ?? "");
}

export async function completeSignIn(): Promise<void> {
  if (MODE === "oidc") await um().signinRedirectCallback();
}

export async function stepUp(): Promise<void> {
  if (MODE === "oidc") return um().signinRedirect({ prompt: "login" });
  await signIn(sessionStorage.getItem("cm_admin_email") ?? undefined);
}

export async function signOut(): Promise<void> {
  sessionStorage.clear();
  if (MODE === "oidc") await um().removeUser();
  window.location.href = "/sign-in";
}
