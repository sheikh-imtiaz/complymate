"use client";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Card, CardContent, CardHeader, CardTitle, PageHeader, Table, TBody, TD, TH, THead, TR } from "@complymate/ui";
import { get, put } from "@/lib/api-client";

interface Flags { defaults: Record<string, boolean>; global: Record<string, boolean>; tenants: { tenant_id: string; key: string; enabled: boolean }[] }

export default function FeatureFlagsPage() {
  const qc = useQueryClient();
  const { data } = useQuery({ queryKey: ["flags"], queryFn: () => get<Flags>("/platform/feature-flags") });
  if (!data) return null;
  return (
    <>
      <PageHeader title="Feature flags" description="Global defaults. Override per tenant from the tenant page." />
      <Card>
        <CardHeader><CardTitle>Global</CardTitle></CardHeader>
        <CardContent className="grid gap-2 md:grid-cols-3">
          {Object.keys(data.defaults).map((key) => {
            const value = data.global[key] ?? data.defaults[key];
            return (
              <label key={key} className="flex items-center gap-2 text-sm">
                <input type="checkbox" checked={value} onChange={async (e) => { await put("/platform/feature-flags", { key, enabled: e.target.checked }); void qc.invalidateQueries({ queryKey: ["flags"] }); }} />
                {key.replace(/_/g, " ")}
              </label>
            );
          })}
        </CardContent>
      </Card>
      <Card className="mt-6">
        <CardHeader><CardTitle>Tenant overrides</CardTitle></CardHeader>
        <CardContent>
          <Table>
            <THead><TR><TH>Tenant</TH><TH>Flag</TH><TH>Enabled</TH></TR></THead>
            <TBody>{data.tenants.map((t) => <TR key={`${t.tenant_id}-${t.key}`}><TD className="font-mono text-xs">{t.tenant_id}</TD><TD>{t.key}</TD><TD>{String(t.enabled)}</TD></TR>)}</TBody>
          </Table>
        </CardContent>
      </Card>
    </>
  );
}
