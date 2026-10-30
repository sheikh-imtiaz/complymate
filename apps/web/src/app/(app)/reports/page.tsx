"use client";
import Link from "next/link";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import type { ReportJob } from "@complymate/api-types";
import { Badge, Button, Card, CardContent, CardDescription, CardHeader, CardTitle, PageHeader, Table, TBody, TD, TH, THead, TR } from "@complymate/ui";
import { get, post } from "@/lib/api-client";
import { formatDateTime } from "@/lib/format";
import { usePermissions } from "@/hooks/usePermission";

export default function ReportsPage() {
  const qc = useQueryClient();
  const can = usePermissions();
  const { data: types = {} } = useQuery({ queryKey: ["report-types"], queryFn: () => get<Record<string, string>>("/reports/types") });
  const { data: jobs = [] } = useQuery({ queryKey: ["report-jobs"], queryFn: () => get<ReportJob[]>("/reports/jobs/list"), refetchInterval: 10_000 });
  const pack = useMutation({ mutationFn: () => post("/reports/regulator-pack"), onSuccess: () => void qc.invalidateQueries({ queryKey: ["report-jobs"] }) });
  async function openExport(id: string) {
    const { url } = await get<{ url: string }>(`/exports/${id}/download`);
    window.location.href = url;
  }
  return (
    <>
      <PageHeader title="Reports" description="Registers, summaries and a one-click regulator pack."
        actions={can("report:export") ? <Button onClick={() => pack.mutate()} loading={pack.isPending}>Build regulator pack</Button> : null} />
      <div className="grid gap-4 md:grid-cols-3">
        {Object.entries(types).map(([key, label]) => (
          <Link key={key} href={`/reports/${key}`}>
            <Card className="h-full hover:border-brand-300"><CardHeader><CardTitle>{label}</CardTitle><CardDescription>View, filter and export</CardDescription></CardHeader></Card>
          </Link>
        ))}
      </div>
      <Card className="mt-6">
        <CardHeader><CardTitle>Report jobs</CardTitle></CardHeader>
        <CardContent>
          <Table>
            <THead><TR><TH>Report</TH><TH>Status</TH><TH>Schedule</TH><TH>Requested</TH><TH /></TR></THead>
            <TBody>
              {jobs.map((j) => (
                <TR key={j.id}>
                  <TD>{j.report_type}</TD><TD><Badge tone={j.status === "done" ? "success" : j.status === "failed" ? "danger" : "info"}>{j.status}</Badge></TD>
                  <TD>{j.schedule_cron ?? "—"}</TD><TD>{formatDateTime(j.created_at)}</TD>
                  <TD className="text-right">{j.export_id ? <Button size="sm" variant="secondary" onClick={() => void openExport(j.export_id!)}>Download</Button> : null}</TD>
                </TR>
              ))}
            </TBody>
          </Table>
        </CardContent>
      </Card>
    </>
  );
}
