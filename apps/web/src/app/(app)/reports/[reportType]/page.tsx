"use client";
import { use, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Button, Card, CardContent, CardHeader, CardTitle, Field, Input, PageHeader, Select, Spinner, Table, TBody, TD, TH, THead, TR } from "@complymate/ui";
import { ReportExportButton } from "@/components/reports/ReportExportButton";
import { get, post } from "@/lib/api-client";
import { usePermissions } from "@/hooks/usePermission";

interface Report { columns: string[]; rows: Record<string, unknown>[]; total: number }

export default function ReportPage({ params }: { params: Promise<{ reportType: string }> }) {
  const { reportType } = use(params);
  const can = usePermissions();
  const [filters, setFilters] = useState<Record<string, string>>({});
  const qs = new URLSearchParams(Object.fromEntries(Object.entries(filters).filter(([, v]) => v)));
  const { data, isLoading } = useQuery({ queryKey: ["report", reportType, qs.toString()], queryFn: () => get<Report>(`/reports/${reportType}?${qs}`) });
  const [schedule, setSchedule] = useState({ cron: "0 8 * * 1", recipients: "", format: "xlsx" });
  return (
    <>
      <PageHeader title={reportType.replace(/-/g, " ").replace(/\b\w/g, (c) => c.toUpperCase())}
        actions={can("report:export") ? (
          <>
            <ReportExportButton path={`/reports/${reportType}?format=csv&${qs}`} filename={`${reportType}.csv`} label="CSV" />
            <ReportExportButton path={`/reports/${reportType}?format=xlsx&${qs}`} filename={`${reportType}.xlsx`} label="XLSX" />
          </>
        ) : null} />
      {reportType === "audit-trail" ? (
        <div className="mb-4 grid gap-3 md:grid-cols-4">
          <Input placeholder="Action" onChange={(e) => setFilters({ ...filters, action: e.target.value })} />
          <Input placeholder="Resource id" onChange={(e) => setFilters({ ...filters, resource_id: e.target.value })} />
          <Input type="date" onChange={(e) => setFilters({ ...filters, date_from: e.target.value })} aria-label="From" />
          <Input type="date" onChange={(e) => setFilters({ ...filters, date_to: e.target.value })} aria-label="To" />
        </div>
      ) : null}
      <Card>
        <CardContent className="pt-5">
          {isLoading || !data ? <Spinner /> : (
            <>
              <Table>
                <THead><TR>{data.columns.map((c) => <TH key={c}>{c.replace(/_/g, " ")}</TH>)}</TR></THead>
                <TBody>{data.rows.map((r, i) => <TR key={i}>{data.columns.map((c) => <TD key={c}>{r[c] == null ? "—" : String(r[c])}</TD>)}</TR>)}</TBody>
              </Table>
              <p className="mt-2 text-xs text-slate-500">Showing {data.rows.length} of {data.total}</p>
            </>
          )}
        </CardContent>
      </Card>
      {can("report:export") ? (
        <Card className="mt-6">
          <CardHeader><CardTitle>Email this report on a schedule (Practice plan)</CardTitle></CardHeader>
          <CardContent className="grid gap-3 md:grid-cols-4">
            <Field label="Cron (Sydney time)"><Input value={schedule.cron} onChange={(e) => setSchedule({ ...schedule, cron: e.target.value })} /></Field>
            <Field label="Recipients (comma separated)"><Input value={schedule.recipients} onChange={(e) => setSchedule({ ...schedule, recipients: e.target.value })} /></Field>
            <Field label="Format"><Select value={schedule.format} onChange={(e) => setSchedule({ ...schedule, format: e.target.value })}><option value="xlsx">XLSX</option><option value="csv">CSV</option></Select></Field>
            <div className="flex items-end"><Button onClick={() => void post("/reports/schedules", { report_type: reportType, cron: schedule.cron, format: schedule.format, recipients: schedule.recipients.split(",").map((s) => s.trim()).filter(Boolean) })}>Schedule</Button></div>
          </CardContent>
        </Card>
      ) : null}
    </>
  );
}
