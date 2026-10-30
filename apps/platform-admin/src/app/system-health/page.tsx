"use client";
import { useQuery } from "@tanstack/react-query";
import { Badge, Card, CardContent, CardHeader, CardTitle, PageHeader, Stat, Table, TBody, TD, TH, THead, TR } from "@complymate/ui";
import { get, post } from "@/lib/api-client";
import { Button } from "@complymate/ui";

interface Health {
  database: string;
  jobs: { watchlists?: { source: string; label: string; entries: number; fetched_at: string }[]; kb_sources_not_checked_90_days?: number; queues?: string };
  chain_verifications: { tenant_id: string | null; ok: boolean; checked: number; reason: string | null; checked_at: string }[];
  llm_spend_month_usd: number;
  llm_budget_usd: number;
}

export default function SystemHealthPage() {
  const { data } = useQuery({ queryKey: ["health"], queryFn: () => get<Health>("/platform/system-health"), refetchInterval: 30_000 });
  if (!data) return null;
  const broken = data.chain_verifications.filter((v) => !v.ok);
  return (
    <>
      <PageHeader title="System health" actions={<Button variant="secondary" onClick={() => void post("/platform/watchlists/refresh")}>Refresh sanctions lists</Button>} />
      <div className="grid gap-4 md:grid-cols-4">
        <Stat label="Database" value={data.database} tone="success" />
        <Stat label="Audit chain breaks" value={broken.length} tone={broken.length ? "danger" : "success"} />
        <Stat label="LLM spend" value={`US$${data.llm_spend_month_usd.toFixed(2)}`} hint={`of US$${data.llm_budget_usd}`} />
        <Stat label="Stale rule sources" value={data.jobs.kb_sources_not_checked_90_days ?? 0} tone={(data.jobs.kb_sources_not_checked_90_days ?? 0) > 0 ? "warning" : undefined} />
      </div>
      <Card className="mt-6">
        <CardHeader><CardTitle>Sanctions lists</CardTitle></CardHeader>
        <CardContent>
          <Table>
            <THead><TR><TH>Source</TH><TH>Version</TH><TH>Entries</TH><TH>Fetched</TH></TR></THead>
            <TBody>{(data.jobs.watchlists ?? []).map((w) => <TR key={w.source}><TD>{w.source}</TD><TD>{w.label}</TD><TD>{w.entries}</TD><TD>{new Date(w.fetched_at).toLocaleString("en-AU")}</TD></TR>)}</TBody>
          </Table>
        </CardContent>
      </Card>
      <Card className="mt-6">
        <CardHeader><CardTitle>Audit chain verifications</CardTitle></CardHeader>
        <CardContent>
          <Table>
            <THead><TR><TH>Tenant</TH><TH>Result</TH><TH>Events</TH><TH>Checked</TH></TR></THead>
            <TBody>{data.chain_verifications.map((v, i) => <TR key={i}><TD className="font-mono text-xs">{v.tenant_id ?? "platform"}</TD><TD><Badge tone={v.ok ? "success" : "danger"}>{v.ok ? "ok" : v.reason}</Badge></TD><TD>{v.checked}</TD><TD>{new Date(v.checked_at).toLocaleString("en-AU")}</TD></TR>)}</TBody>
          </Table>
          <p className="mt-2 text-xs text-slate-500">{data.jobs.queues}</p>
        </CardContent>
      </Card>
    </>
  );
}
