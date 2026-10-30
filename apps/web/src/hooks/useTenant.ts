"use client";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import type { Me } from "@complymate/api-types";
import { get } from "@/lib/api-client";
import { getTenantId, setTenantId } from "@/lib/auth";

export function useMe() {
  return useQuery({ queryKey: ["me", getTenantId()], queryFn: () => get<Me>("/auth/me"), staleTime: 60_000, retry: false });
}

export function useTenant() {
  const qc = useQueryClient();
  const me = useMe();
  const tenantId = me.data?.tenant_id ?? getTenantId();
  const current = me.data?.memberships.find((m) => m.tenant_id === tenantId);
  return {
    me: me.data,
    isLoading: me.isLoading,
    error: me.error,
    tenantId,
    tenantName: current?.tenant_name,
    role: me.data?.role_key ?? null,
    switchTenant: (id: string) => {
      setTenantId(id);
      qc.clear();
      window.location.href = "/dashboard";
    },
  };
}
