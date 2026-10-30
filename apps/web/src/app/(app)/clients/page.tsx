"use client";
import { useState } from "react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import type { ClientListItem, Page } from "@complymate/api-types";
import { Button, Card, CardContent, EmptyState, Input, PageHeader, Select, Spinner, Table, TBody, TD, TH, THead, TR } from "@complymate/ui";
import { RiskBadge, StatusBadge } from "@/components/clients/RiskBadge";
import { ReportExportButton } from "@/components/reports/ReportExportButton";
import { get } from "@/lib/api-client";
import { formatDate, humanize, isOverdue } from "@/lib/format";
import { usePermissions } from "@/hooks/usePermission";

export default function ClientsPage() {
  const can = usePermissions();
  const [q, setQ] = useState("");
  const [status, setStatus] = useState("");
  const [risk, setRisk] = useState("");
  const params = new URLSearchParams({ ...(q && { q }), ...(status && { status }), ...(risk && { risk }), limit: "100" });
  const { data, isLoading } = useQuery({ queryKey: ["clients", q, status, risk], queryFn: () => get<Page<ClientListItem>>(`/clients?${params}`) });
  return (
    <>
      <PageHeader
        title="Clients"
        description="Customer due diligence records, risk ratings and review dates."
        actions={
          <>
            {can("client:export") ? <ReportExportButton path="/clients/export?format=xlsx" filename="client-register.xlsx" label="Export register" /> : null}
            {can("client:create") ? <Button asChild><Link href="/clients/new">New client</Link></Button> : null}
          </>
        }
      />
      <Card>
        <CardContent className="space-y-4 pt-5">
          <div className="grid gap-3 md:grid-cols-4">
            <Input placeholder="Search by name" value={q} onChange={(e) => setQ(e.target.value)} />
            <Select value={status} onChange={(e) => setStatus(e.target.value)} aria-label="Status">
              <option value="">All statuses</option>
              {["pending", "approved", "declined", "exited"].map((s) => <option key={s} value={s}>{humanize(s)}</option>)}
            </Select>
            <Select value={risk} onChange={(e) => setRisk(e.target.value)} aria-label="Risk">
              <option value="">All risk levels</option>
              {["low", "medium", "high", "unassessed"].map((s) => <option key={s} value={s}>{humanize(s)}</option>)}
            </Select>
          </div>
          {isLoading ? <Spinner /> : !data?.items.length ? (
            <EmptyState title="No clients yet" description="Add your first client to start customer due diligence." />
          ) : (
            <Table>
              <THead><TR><TH>Name</TH><TH>Type</TH><TH>Status</TH><TH>Risk</TH><TH>Next review</TH></TR></THead>
              <TBody>
                {data.items.map((c) => (
                  <TR key={c.id}>
                    <TD><Link href={`/clients/${c.id}`} className="font-medium text-brand-700 hover:underline">{c.display_name}</Link></TD>
                    <TD>{humanize(c.client_type)}</TD>
                    <TD><StatusBadge status={c.status} /></TD>
                    <TD><RiskBadge level={c.risk_level} /></TD>
                    <TD className={isOverdue(c.next_review_date) ? "font-medium text-risk-high" : ""}>{formatDate(c.next_review_date)}</TD>
                  </TR>
                ))}
              </TBody>
            </Table>
          )}
          {data ? <p className="text-xs text-slate-500">{data.total} client(s)</p> : null}
        </CardContent>
      </Card>
    </>
  );
}
