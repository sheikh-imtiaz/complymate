"use client";
import { useState } from "react";
import type { ProgramVersion } from "@complymate/api-types";
import { Badge, Button, Card, CardContent, CardHeader, CardTitle, Textarea } from "@complymate/ui";
import { post } from "@/lib/api-client";
import { formatDateTime, humanize } from "@/lib/format";
import { usePermissions } from "@/hooks/usePermission";
import { useTenant } from "@/hooks/useTenant";

/** draft → AMLCO review → Senior Manager / Owner sign-off. The submitter cannot sign off (four-eyes). */
export function ApprovalPanel({ version, onChanged }: { version: ProgramVersion; onChanged: () => void }) {
  const can = usePermissions();
  const { role, me } = useTenant();
  const [comment, setComment] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function act(path: string, body?: unknown) {
    setBusy(true);
    setError(null);
    try {
      await post(`/program/versions/${version.id}/${path}`, body);
      setComment("");
      onChanged();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Action failed");
    } finally {
      setBusy(false);
    }
  }

  const isReviewer = role === "amlco" || role === "owner";
  const isSigner = can("program:approve") && version.submitted_by !== me?.user_id;

  return (
    <Card>
      <CardHeader>
        <CardTitle>Approval</CardTitle>
        <div><Badge tone={version.status === "approved" ? "success" : "info"}>{humanize(version.status)}</Badge></div>
      </CardHeader>
      <CardContent className="space-y-3 text-sm">
        <ol className="space-y-1 text-slate-600">
          {version.approvals.map((a) => (
            <li key={a.id}>{humanize(a.step)}: <strong>{a.decision}</strong> by {humanize(a.decided_role)} · {formatDateTime(a.decided_at)}{a.comment ? ` — ${a.comment}` : ""}</li>
          ))}
        </ol>
        {version.status === "draft" && can("program:update") ? (
          <Button loading={busy} onClick={() => void act("submit")}>Submit for AMLCO review</Button>
        ) : null}
        {(version.status === "in_review" && isReviewer) || (version.status === "awaiting_signoff" && isSigner) ? (
          <div className="space-y-2">
            <Textarea placeholder="Comment (optional)" value={comment} onChange={(e) => setComment(e.target.value)} rows={2} />
            <div className="flex gap-2">
              <Button loading={busy} onClick={() => void act(version.status === "in_review" ? "review" : "sign-off", { approve: true, comment })}>
                {version.status === "in_review" ? "Approve review" : "Sign off program"}
              </Button>
              <Button variant="secondary" loading={busy} onClick={() => void act(version.status === "in_review" ? "review" : "sign-off", { approve: false, comment })}>
                Return for changes
              </Button>
            </div>
          </div>
        ) : null}
        {version.status === "awaiting_signoff" && !isSigner && can("program:approve") ? (
          <p className="text-amber-700">You submitted this version, so another senior manager or owner must sign it off.</p>
        ) : null}
        {error ? <p className="text-red-600">{error}</p> : null}
      </CardContent>
    </Card>
  );
}
