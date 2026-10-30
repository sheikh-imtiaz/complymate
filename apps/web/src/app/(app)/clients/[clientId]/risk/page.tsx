"use client";
import { use } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import type { Assessment, EddTask } from "@complymate/api-types";
import { Alert, Badge, Button, Card, CardContent, CardHeader, CardTitle, EmptyState, Table, TBody, TD, TH, THead, TR } from "@complymate/ui";
import { RiskBadge } from "@/components/clients/RiskBadge";
import { get, patch, post } from "@/lib/api-client";
import { formatDate, formatDateTime } from "@/lib/format";
import { usePermissions } from "@/hooks/usePermission";

export default function RiskPage({ params }: { params: Promise<{ clientId: string }> }) {
  const { clientId } = use(params);
  const qc = useQueryClient();
  const can = usePermissions();
  const { data: assessments = [] } = useQuery({ queryKey: ["risk", clientId], queryFn: () => get<Assessment[]>(`/clients/${clientId}/risk`) });
  const { data: edd = [] } = useQuery({ queryKey: ["edd", clientId], queryFn: () => get<EddTask[]>(`/clients/${clientId}/edd-tasks`) });
  const refresh = () => ["risk", "edd", "client"].forEach((k) => void qc.invalidateQueries({ queryKey: [k, clientId] }));
  const run = useMutation({ mutationFn: () => post(`/clients/${clientId}/risk`), onSuccess: refresh });
  const latest = assessments.find((a) => a.status !== "superseded");
  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        {can("risk:create") ? <Button onClick={() => run.mutate()} loading={run.isPending}>Run risk assessment</Button> : null}
        <p className="text-sm text-slate-500">The rating comes from your firm&apos;s rule set (deterministic, not AI). Every reason is shown.</p>
      </div>
      {!latest ? <EmptyState title="Not assessed yet" description="Screen the client first, then run the risk assessment." /> : (
        <Card>
          <CardHeader className="flex-row items-center justify-between">
            <CardTitle>Current rating</CardTitle>
            <div className="flex items-center gap-2"><RiskBadge level={latest.override_level ?? latest.level} /><Badge>Score {latest.score}</Badge><Badge>{latest.rules_version}</Badge></div>
          </CardHeader>
          <CardContent>
            {latest.override_level ? <Alert tone="info" className="mb-3">Overridden to {latest.override_level}: {latest.override_reason}</Alert> : null}
            {latest.status === "proposed" ? <Alert tone="warning" className="mb-3">High-risk decision awaiting second-person approval.</Alert> : null}
            <Table>
              <THead><TR><TH>Factor</TH><TH>Category</TH><TH>Points</TH></TR></THead>
              <TBody>{latest.reasons.map((r) => <TR key={String(r.factor_id)}><TD>{String(r.description)}</TD><TD>{String(r.category)}</TD><TD>{String(r.points)}</TD></TR>)}</TBody>
            </Table>
            <p className="mt-2 text-xs text-slate-400">Assessed {formatDateTime(latest.created_at)}</p>
          </CardContent>
        </Card>
      )}
      {edd.length ? (
        <Card>
          <CardHeader><CardTitle>Enhanced due diligence</CardTitle></CardHeader>
          <CardContent>
            <Table>
              <THead><TR><TH>Task</TH><TH>Due</TH><TH>Status</TH><TH /></TR></THead>
              <TBody>
                {edd.map((t) => (
                  <TR key={t.id}>
                    <TD>{t.title}</TD><TD>{formatDate(t.due_date)}</TD><TD><Badge tone={t.status === "done" ? "success" : "warning"}>{t.status}</Badge></TD>
                    <TD className="text-right">{t.status === "open" && can("client:update") ? (
                      <Button size="sm" variant="secondary" onClick={async () => { await patch(`/edd-tasks/${t.id}`, { status: "done", note: window.prompt("Evidence / note") ?? "" }); refresh(); }}>Complete</Button>
                    ) : null}</TD>
                  </TR>
                ))}
              </TBody>
            </Table>
          </CardContent>
        </Card>
      ) : null}
      {assessments.length > 1 ? (
        <Card>
          <CardHeader><CardTitle>History</CardTitle></CardHeader>
          <CardContent className="text-sm">{assessments.map((a) => <p key={a.id}>{formatDateTime(a.created_at)} — {a.level} ({a.score}) · {a.status}</p>)}</CardContent>
        </Card>
      ) : null}
    </div>
  );
}
