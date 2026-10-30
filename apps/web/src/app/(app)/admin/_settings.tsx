"use client";
import { useQuery, useQueryClient, useMutation } from "@tanstack/react-query";
import type { TenantSettings } from "@complymate/api-types";
import { get, patch } from "@/lib/api-client";

export function useSettings() {
  const qc = useQueryClient();
  const query = useQuery({ queryKey: ["settings"], queryFn: () => get<TenantSettings>("/tenants/current/settings") });
  const save = useMutation({
    mutationFn: (changes: Partial<TenantSettings>) => patch<TenantSettings>("/tenants/current/settings", changes),
    onSuccess: (data) => qc.setQueryData(["settings"], data),
  });
  return { settings: query.data, save };
}
