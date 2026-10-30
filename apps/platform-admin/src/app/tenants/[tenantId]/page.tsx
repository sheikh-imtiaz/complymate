"use client";
import { use } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Alert, Badge, Button, Card, CardContent, CardHeader, CardTitle, PageHeader, Spinner } from "@complymate/ui";
import { get, post, put } from "@/lib/api-client";

interface Detail {
  tenant: Record<string, unknown>;
  subscription: Record<string, unknown> | null;
  members: number;
  usage: Record<string, number>;
  flags: Record<string, boolean>;
  tenant_flag_overrides: Record<string, boolean>;
  llm_cost_month_usd: number;
}

export default function TenantDetail({ params }: { params: Promise<{ tenantId: string }> }) {
  const { tenantId } = use(params);
  const qc = useQueryClient();
  const { data } = useQuery({ queryKey: ["tenant", tenantId], queryFn: () => get<Detail>(`/platform/tenants/${tenantId}`) });
  const refresh = () => void qc.invalidateQueries({ queryKey: ["tenant", tenantId] });
  const status = useMutation({
    mutationFn: (action: "suspend" | "reactivate") => post(`/platform/tenants/${tenantId}/${action}`, { reason: window.prompt("Reason (recorded in the audit log)") ?? "" }),
    onSuccess: refresh,
  });
  if (!data) return <Spinner />;
  const t = data.tenant;
  return (
    <>
      <PageHeader title={String(t.name)} description={`${t.jurisdiction} · ${t.plan_code} plan · ${data.members} users`}
        actions={t.status === "suspended"
          ? <Button onClick={() => status.mutate("reactivate")}>Reactivate</Button>
          : <Button variant="destructive" onClick={() => status.mutate("suspend")}>Suspend</Button>} />
      {status.error ? <Alert tone="danger" className="mb-4">{(status.error as Error).message}</Alert> : null}
      <div className="grid gap-4 md:grid-cols-3">
        <Card><CardHeader><CardTitle>Status</CardTitle></CardHeader><CardContent><Badge>{String(t.status)}</Badge> · subscription {String(data.subscription?.status ?? "none")}</CardContent></Card>
        <Card><CardHeader><CardTitle>Usage (month)</CardTitle></CardHeader><CardContent className="text-sm">{Object.entries(data.usage).map(([k, v]) => <p key={k}>{k}: {v}</p>)}</CardContent></Card>
        <Card><CardHeader><CardTitle>LLM cost (month)</CardTitle></CardHeader><CardContent>US${data.llm_cost_month_usd.toFixed(2)}</CardContent></Card>
      </div>
      <Card className="mt-6">
        <CardHeader><CardTitle>Feature flags for this tenant</CardTitle></CardHeader>
        <CardContent className="grid gap-2 md:grid-cols-3">
          {Object.entries(data.flags).map(([key, enabled]) => (
            <label key={key} className="flex items-center gap-2 text-sm">
              <input type="checkbox" checked={enabled} onChange={async (e) => { await put("/platform/feature-flags", { key, enabled: e.target.checked, tenant_id: tenantId }); refresh(); }} />
              {key.replace(/_/g, " ")}{key in data.tenant_flag_overrides ? <Badge tone="info">override</Badge> : null}
            </label>
          ))}
        </CardContent>
      </Card>
      <p className="mt-4 text-xs text-slate-500">Client records, ID documents and suspicious matter reports are never visible from the platform console.</p>
    </>
  );
}
