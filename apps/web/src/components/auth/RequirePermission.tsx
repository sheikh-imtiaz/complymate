"use client";
import type { ReactNode } from "react";
import { Alert } from "@complymate/ui";
import { usePermission } from "@/hooks/usePermission";

/** Hides UI the user cannot use. The API enforces the same permission (and RLS) regardless. */
export function RequirePermission({ permission, children, fallback }: { permission: string; children: ReactNode; fallback?: ReactNode }) {
  const { allowed } = usePermission(permission);
  if (allowed) return <>{children}</>;
  return fallback === undefined ? (
    <Alert tone="warning" title="Not available">You don&apos;t have access to this page. Ask your firm owner if you need it.</Alert>
  ) : (
    <>{fallback}</>
  );
}
