"use client";
import { useState } from "react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import type { TenantSummary } from "@complymate/api-types";
import { Badge, Card, CardContent, Input, PageHeader, Select, Table, TBody, TD, TH, THead, TR } from "@complymate/ui";
import { get } from "@/lib/api-client";

export default function TenantsPage() {
  const [q, setQ] = useState("");
  const [status, setStatus] = useState("");
  const qs = new URLSearchParams({ ...(q && { q }), ...(status && { status }) });
  const { data = [] } = useQuery({ queryKey: ["tenants", q, status], queryFn: () => get<TenantSummary[]>(`/platform/tenants?${qs}`) });
  return (
    <>
      <PageHeader title="Tenants" description="Firms, plans, status and usage this month." />
      <Card>
        <CardContent className="space-y-4 pt-5">
          <div className="flex gap-3">
            <Input placeholder="Search firms" value={q} onChange={(e) => setQ(e.target.value)} className="w-64" />
            <Select value={status} onChange={(e) => setStatus(e.target.value)} className="w-40" aria-label="Status">
              <option value="">All</option>{["trial", "active", "suspended", "cancelled"].map((s) => <option key={s}>{s}</option>)}
            </Select>
          </div>
          <Table>
            <THead><TR><TH>Firm</TH><TH>Jurisdiction</TH><TH>Plan</TH><TH>Status</TH><TH>Users</TH><TH>Agent turns</TH><TH>Documents</TH></TR></THead>
            <TBody>
              {data.map((t) => (
                <TR key={t.id}>
                  <TD><Link href={`/tenants/${t.id}`} className="font-medium text-brand-700 hover:underline">{t.name}</Link></TD>
                  <TD>{t.jurisdiction}</TD><TD>{t.plan_code}</TD>
                  <TD><Badge tone={t.status === "active" ? "success" : t.status === "suspended" ? "danger" : "info"}>{t.status}</Badge></TD>
                  <TD>{t.members}</TD><TD>{t.usage.agent_turns ?? 0}</TD><TD>{t.usage.documents ?? 0}</TD>
                </TR>
              ))}
            </TBody>
          </Table>
        </CardContent>
      </Card>
    </>
  );
}
