"use client";
import { useQuery } from "@tanstack/react-query";
import { Bar, BarChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Card, CardContent, CardHeader, CardTitle, PageHeader, Stat, Table, TBody, TD, TH, THead, TR } from "@complymate/ui";
import { get } from "@/lib/api-client";

interface Usage { period: string; budget_usd: number; total_usd: number; by_tenant_purpose: { tenant: string; purpose: string; calls: number; input_tokens: number; output_tokens: number; cost_usd: number }[] }

export default function UsageCostsPage() {
  const { data } = useQuery({ queryKey: ["usage"], queryFn: () => get<Usage>("/platform/usage-costs") });
  if (!data) return null;
  const byTenant = Object.values(data.by_tenant_purpose.reduce<Record<string, { tenant: string; cost: number }>>((acc, r) => {
    acc[r.tenant] = { tenant: r.tenant, cost: (acc[r.tenant]?.cost ?? 0) + r.cost_usd };
    return acc;
  }, {})).sort((a, b) => b.cost - a.cost).slice(0, 15);
  return (
    <>
      <PageHeader title="Usage and LLM cost" description={`Period ${data.period}`} />
      <div className="grid gap-4 md:grid-cols-2">
        <Stat label="LLM spend this month" value={`US$${data.total_usd.toFixed(2)}`} tone={data.total_usd > data.budget_usd ? "danger" : undefined} hint={`Budget US$${data.budget_usd}`} />
        <Stat label="Agent calls" value={data.by_tenant_purpose.reduce((s, r) => s + r.calls, 0)} />
      </div>
      <Card className="mt-6">
        <CardHeader><CardTitle>Top tenants by cost</CardTitle></CardHeader>
        <CardContent className="h-72">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={byTenant}><XAxis dataKey="tenant" hide /><YAxis /><Tooltip /><Bar dataKey="cost" fill="#0f4c81" /></BarChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>
      <Card className="mt-6">
        <CardContent className="pt-5">
          <Table>
            <THead><TR><TH>Tenant</TH><TH>Purpose</TH><TH>Calls</TH><TH>Tokens in/out</TH><TH>Cost (US$)</TH></TR></THead>
            <TBody>{data.by_tenant_purpose.map((r) => <TR key={`${r.tenant}-${r.purpose}`}><TD>{r.tenant}</TD><TD>{r.purpose}</TD><TD>{r.calls}</TD><TD>{r.input_tokens}/{r.output_tokens}</TD><TD>{r.cost_usd.toFixed(4)}</TD></TR>)}</TBody>
          </Table>
        </CardContent>
      </Card>
    </>
  );
}
