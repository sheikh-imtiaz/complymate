"use client";
import { use, useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import type { SmrDetail } from "@complymate/api-types";
import { Alert, Badge, Button, Card, CardContent, CardHeader, CardTitle, Field, PageHeader, Spinner, Textarea } from "@complymate/ui";
import { Comments } from "@/components/collaboration/Comments";
import { ReportExportButton } from "@/components/reports/ReportExportButton";
import { get, patch, post } from "@/lib/api-client";
import { formatDateTime, humanize } from "@/lib/format";
import { usePermissions } from "@/hooks/usePermission";

const CATEGORIES = ["unusual_transaction", "structuring", "identity_concerns", "source_of_funds", "third_party_payments", "sanctions", "terrorism_financing", "tax_evasion", "fraud", "proceeds_of_crime", "other"];

export default function SmrCasePage({ params }: { params: Promise<{ caseId: string }> }) {
  const { caseId } = use(params);
  const qc = useQueryClient();
  const can = usePermissions();
  const key = ["smr", caseId];
  const { data } = useQuery({ queryKey: key, queryFn: () => get<SmrDetail>(`/smr/${caseId}`) });
  const [grounds, setGrounds] = useState("");
  const [cats, setCats] = useState<string[]>([]);
  const [note, setNote] = useState("");
  useEffect(() => {
    if (data) {
      setGrounds(data.case.grounds ?? "");
      setCats(data.case.suspicion_categories);
    }
  }, [data]);
  const refresh = () => void qc.invalidateQueries({ queryKey: key });
  const save = useMutation({ mutationFn: () => patch(`/smr/${caseId}`, { grounds, suspicion_categories: cats }), onSuccess: refresh });
  const act = useMutation({ mutationFn: ({ path, body }: { path: string; body?: unknown }) => post(`/smr/${caseId}/${path}`, body), onSuccess: refresh });
  if (!data) return <Spinner />;
  const c = data.case;
  const full = can("smr:read");
  const suggestion = c.ai_suggestion as { grounds_summary?: string; missing_information?: string[]; suspicion_categories?: string[] } | null;
  return (
    <>
      <PageHeader title={c.reference} description={`Raised ${formatDateTime(c.created_at)}`} actions={<Badge tone="warning">{humanize(c.status)}</Badge>} />
      <Alert tone="danger" title="Tipping-off warning" className="mb-6">{data.tipping_off_warning}</Alert>
      <div className="grid gap-6 lg:grid-cols-[1fr_340px]">
        <div className="space-y-4">
          <Card><CardHeader><CardTitle>Concern</CardTitle></CardHeader><CardContent className="whitespace-pre-wrap text-sm">{c.summary}</CardContent></Card>
          {c.status === "draft" && !full ? <Button onClick={() => act.mutate({ path: "submit" })}>Send to compliance officer</Button> : null}
          {full ? (
            <Card>
              <CardHeader><CardTitle>Assessment</CardTitle></CardHeader>
              <CardContent className="space-y-3">
                <Field label="Grounds for suspicion"><Textarea rows={5} value={grounds} onChange={(e) => setGrounds(e.target.value)} disabled={!can("smr:update")} /></Field>
                <div className="flex flex-wrap gap-2">
                  {CATEGORIES.map((cat) => (
                    <label key={cat} className="flex items-center gap-1 rounded-full border px-2 py-0.5 text-xs">
                      <input type="checkbox" checked={cats.includes(cat)} onChange={(e) => setCats(e.target.checked ? [...cats, cat] : cats.filter((x) => x !== cat))} />{humanize(cat)}
                    </label>
                  ))}
                </div>
                {can("smr:update") ? (
                  <div className="flex gap-2">
                    <Button size="sm" onClick={() => save.mutate()} loading={save.isPending}>Save</Button>
                    <Button size="sm" variant="secondary" onClick={() => act.mutate({ path: "ai-assist" })} loading={act.isPending}>Structure with agent</Button>
                  </div>
                ) : null}
                {suggestion ? (
                  <Alert tone="info" title="Agent suggestion (you decide)">
                    <p>{suggestion.grounds_summary}</p>
                    {suggestion.missing_information?.length ? <p className="mt-1">Missing: {suggestion.missing_information.join("; ")}</p> : null}
                  </Alert>
                ) : null}
              </CardContent>
            </Card>
          ) : null}
          {full ? (
            <Card>
              <CardHeader><CardTitle>Notes</CardTitle></CardHeader>
              <CardContent className="space-y-2 text-sm">
                {data.notes.map((n) => <p key={n.id} className="rounded bg-slate-50 p-2"><span className="text-xs text-slate-500">{formatDateTime(n.created_at)}</span><br />{n.body}</p>)}
                {can("smr:update") ? (
                  <div className="flex gap-2"><Textarea rows={2} value={note} onChange={(e) => setNote(e.target.value)} /><Button size="sm" onClick={() => { act.mutate({ path: "notes", body: { body: note } }); setNote(""); }}>Add</Button></div>
                ) : null}
              </CardContent>
            </Card>
          ) : null}
          {full ? <Comments resourceType="smr_case" resourceId={caseId} /> : null}
        </div>
        {full ? (
          <Card className="h-fit">
            <CardHeader><CardTitle>Decision</CardTitle></CardHeader>
            <CardContent className="space-y-2">
              {c.status === "under_review" && can("smr:approve") ? (
                <>
                  <Button className="w-full" onClick={() => act.mutate({ path: "decide", body: { report: true, reason: window.prompt("Reason for reporting") ?? "" } })}>Decide: report to AUSTRAC</Button>
                  <Button className="w-full" variant="secondary" onClick={() => act.mutate({ path: "decide", body: { report: false, reason: window.prompt("Reason for not reporting") ?? "" } })}>Decide: no report</Button>
                </>
              ) : null}
              {(c.status === "decided_report" || c.status === "exported") && can("smr:export") ? (
                <ReportExportButton path={`/smr/${caseId}/export`} filename={`${c.reference}.zip`} label="Export for AUSTRAC Online" />
              ) : null}
              {c.decision_reason ? <p className="text-sm text-slate-600">Decision: {c.decision_reason}</p> : null}
              {act.error ? <Alert tone="danger">{(act.error as Error).message}</Alert> : null}
              <p className="text-xs text-slate-500">ComplyMate never submits reports. Lodge manually: 24 hours for terrorism financing, 3 business days otherwise.</p>
            </CardContent>
          </Card>
        ) : null}
      </div>
    </>
  );
}
