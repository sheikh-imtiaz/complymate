// Mirrors the API's permission strings (resource:action[:own|:shared]). The API always re-checks.
export type Scope = "all" | "own" | "shared";

export function scopeFor(permissions: readonly string[] | undefined, permission: string): Scope | null {
  if (!permissions) return null;
  if (permissions.includes(permission)) return "all";
  if (permissions.includes(`${permission}:own`)) return "own";
  if (permissions.includes(`${permission}:shared`)) return "shared";
  return null;
}

export function can(permissions: readonly string[] | undefined, permission: string): boolean {
  return scopeFor(permissions, permission) !== null;
}

export const SMR_ROLES = ["owner", "amlco", "senior_manager"];
