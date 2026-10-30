"use client";
import { can, scopeFor } from "@/lib/permissions";
import { useMe } from "./useTenant";

export function usePermission(permission: string) {
  const { data } = useMe();
  return { allowed: can(data?.permissions, permission), scope: scopeFor(data?.permissions, permission) };
}

export function usePermissions() {
  const { data } = useMe();
  return (permission: string) => can(data?.permissions, permission);
}
