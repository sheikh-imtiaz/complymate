"use client";
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import type { AuditEvent, Page } from "@complymate/api-types";
import { Alert, Button, Card, CardContent, PageHeader, Spinner } from "@complymate/ui";
import { AuditDetailDrawer } from "@/components/audit/AuditDetailDrawer";
import { AuditFilters, type AuditFilterValues } from "@/components/audit/AuditFilters";
import { AuditTable } from "@/components/audit/AuditTable";
import { RequirePermission } from "@/components/auth/RequirePermission";
import { ReportExportButton } from "@/components/reports/ReportExportButton";
import { get } from "@/lib/api-client";
import { usePermissions } from "@/hooks/usePermission";

export default function AuditLogPage() {
  const can = usePermissions();
  const [filters, setFilters] = useState<AuditFilterValues>({});
  const [offset, setOffset] = useState(0);
  const [selected, setSelected] = useState<AuditEvent | null>(null);
  const qs = new URLSearchParams(Object.fromEntries(Object.entries({ ...filters, offset: String(offset), limit: "100" }).filter(([, v]) => v)) as Record<string, string>);
  const { data, isLoading } = useQuery({ queryKey: ["audit", qs.toString()], queryFn: () => get<Page<AuditEvent>>(`/audit?${qs}`) });
  const { data: chain } = useQuery({ queryKey: ["audit-verify"], queryFn: () => get<{ ok: boolean; checked: number; reason: string | null }>("/audit/verify") });
  return (
    <RequirePermission permission="audit:read">
      <PageHeader title="Audit log" description="Append-only, hash-chained record of every change, approval, export and AI decision."
        actions={can("audit:export") ? <ReportExportButton path={`/audit/export?${qs}`} filename="audit-trail.csv" /> : null} />
      {chain ? <Alert tone={chain.ok ? "success" : "danger"} className="mb-4" title={chain.ok ? "Hash chain verified" : "Hash chain problem"}>{chain.ok ? `${chain.checked} events checked.` : chain.reason}</Alert> : null}
      <Card>
        <CardContent className="space-y-4 pt-5">
          <AuditFilters value={filters} onChange={(v) => { setFilters(v); setOffset(0); }} />
          {isLoading || !data ? <Spinner /> : <AuditTable data={data.items} onSelect={setSelected} />}
          {data ? (
            <div className="flex items-center justify-between text-sm text-slate-500">
              <span>{data.total} events</span>
              <div className="flex gap-2">
                <Button size="sm" variant="secondary" disabled={offset === 0} onClick={() => setOffset(Math.max(0, offset - 100))}>Previous</Button>
                <Button size="sm" variant="secondary" disabled={offset + 100 >= data.total} onClick={() => setOffset(offset + 100)}>Next</Button>
              </div>
            </div>
          ) : null}
        </CardContent>
      </Card>
      <AuditDetailDrawer event={selected} onClose={() => setSelected(null)} />
    </RequirePermission>
  );
}
