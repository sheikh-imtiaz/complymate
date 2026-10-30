"use client";
import Link from "next/link";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import type { Program } from "@complymate/api-types";
import { Alert, Badge, Button, Card, CardContent, CardHeader, CardTitle, PageHeader, Spinner, Table, TBody, TD, TH, THead, TR } from "@complymate/ui";
import { get, post } from "@/lib/api-client";
import { formatDate, humanize } from "@/lib/format";
import { usePermissions } from "@/hooks/usePermission";

export default function ProgramPage() {
  const qc = useQueryClient();
  const can = usePermissions();
  const { data, isLoading } = useQuery({ queryKey: ["program"], queryFn: () => get<Program>("/program") });
  const draft = useMutation({ mutationFn: () => post("/program/draft", {}), onSuccess: () => void qc.invalidateQueries({ queryKey: ["program"] }) });
  const newVersion = useMutation({
    mutationFn: () => post("/program/versions", { change_summary: window.prompt("What is changing in this version?") ?? "Annual review" }),
    onSuccess: () => void qc.invalidateQueries({ queryKey: ["program"] }),
  });
  if (isLoading || !data) return <Spinner />;
  const current = data.versions.find((v) => v.id === data.current_version_id);
  return (
    <>
      <PageHeader
        title="AML/CTF program"
        description="Build, review and approve your program. The agent drafts sections with citations; your AMLCO and governing body decide."
        actions={can("program:update") ? (
          <>
            <Button variant="secondary" asChild><Link href="/program/interview">Interview ({Math.round(data.interview_progress * 100)}%)</Link></Button>
            {current?.locked ? <Button onClick={() => newVersion.mutate()} loading={newVersion.isPending}>Start new version</Button>
              : <Button onClick={() => draft.mutate()} loading={draft.isPending}>Draft with agent</Button>}
          </>
        ) : null}
      />
      {draft.error ? <Alert tone="danger" className="mb-4">{(draft.error as Error).message}</Alert> : null}
      {current?.draft_status && ["queued", "running"].includes(current.draft_status) ? <Alert tone="info" className="mb-4">The agent is drafting your sections. You&apos;ll get a notification when it&apos;s ready.</Alert> : null}
      <div className="grid gap-4 md:grid-cols-3">
        <Card><CardHeader><CardTitle>Status</CardTitle></CardHeader><CardContent><Badge tone={data.status === "approved" ? "success" : "warning"}>{humanize(data.status)}</Badge></CardContent></Card>
        <Card><CardHeader><CardTitle>Next annual review</CardTitle></CardHeader><CardContent>{formatDate(data.next_review_due)}</CardContent></Card>
        <Card><CardHeader><CardTitle>Current version</CardTitle></CardHeader><CardContent>{current ? <Link className="text-brand-600 hover:underline" href={`/program/${current.id}`}>Version {current.version_number} — {humanize(current.status)}</Link> : "—"}</CardContent></Card>
      </div>
      <Card className="mt-6">
        <CardHeader><CardTitle>Version history</CardTitle></CardHeader>
        <CardContent>
          <Table>
            <THead><TR><TH>Version</TH><TH>Status</TH><TH>Summary</TH><TH>Approved</TH><TH /></TR></THead>
            <TBody>
              {data.versions.map((v) => (
                <TR key={v.id}>
                  <TD>v{v.version_number}</TD>
                  <TD><Badge tone={v.status === "approved" ? "success" : "neutral"}>{humanize(v.status)}</Badge></TD>
                  <TD>{v.change_summary ?? "—"}</TD>
                  <TD>{formatDate(v.approved_at)}</TD>
                  <TD className="text-right">
                    <Link className="text-brand-600 hover:underline" href={`/program/${v.id}`}>Open</Link>
                    {data.approved_version_id && v.id !== data.approved_version_id ? (
                      <Link className="ml-3 text-brand-600 hover:underline" href={`/program/${v.id}/compare?with=${data.approved_version_id}`}>Compare</Link>
                    ) : null}
                  </TD>
                </TR>
              ))}
            </TBody>
          </Table>
        </CardContent>
      </Card>
    </>
  );
}
