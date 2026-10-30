"use client";
import { use, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import type { Client } from "@complymate/api-types";
import { Alert, Button, Card, CardContent, CardHeader, CardTitle, Checkbox, Spinner } from "@complymate/ui";
import { ClientForm, type ClientFormValues } from "@/components/clients/ClientForm";
import { Comments } from "@/components/collaboration/Comments";
import { get, patch, post } from "@/lib/api-client";
import { formatDate } from "@/lib/format";
import { usePermissions } from "@/hooks/usePermission";

interface Cdd { client_type: string; missing_fields: string[]; verify_with_one_of: string[][]; documents_present: string[]; checklist: string[]; verifications: { id: string; result: string; checklist: Record<string, boolean> }[] }

export default function ClientOverview({ params }: { params: Promise<{ clientId: string }> }) {
  const { clientId } = use(params);
  const qc = useQueryClient();
  const can = usePermissions();
  const { data: client } = useQuery({ queryKey: ["client", clientId], queryFn: () => get<Client>(`/clients/${clientId}`) });
  const { data: cdd } = useQuery({ queryKey: ["cdd", clientId], queryFn: () => get<Cdd>(`/clients/${clientId}/cdd`) });
  const [checked, setChecked] = useState<Record<string, boolean>>({});
  const [editing, setEditing] = useState(false);
  const refresh = () => {
    void qc.invalidateQueries({ queryKey: ["client", clientId] });
    void qc.invalidateQueries({ queryKey: ["cdd", clientId] });
  };
  const update = useMutation({ mutationFn: (v: ClientFormValues) => patch(`/clients/${clientId}`, v), onSuccess: () => { setEditing(false); refresh(); } });
  const verify = useMutation({
    mutationFn: () => post(`/clients/${clientId}/verifications`, { method: "manual", checklist: checked, result: Object.values(checked).every(Boolean) && Object.keys(checked).length === cdd?.checklist.length ? "passed" : "pending" }),
    onSuccess: refresh,
  });
  const action = useMutation({ mutationFn: (path: string) => post(`/clients/${clientId}/${path}`, path === "decline" || path === "exit" ? { reason: window.prompt("Reason") ?? "" } : undefined), onSuccess: refresh });
  if (!client || !cdd) return <Spinner />;

  return (
    <div className="grid gap-6 lg:grid-cols-[1fr_340px]">
      <div className="space-y-6">
        <Card>
          <CardHeader className="flex-row items-center justify-between"><CardTitle>Details</CardTitle>{can("client:update") ? <Button size="sm" variant="secondary" onClick={() => setEditing(!editing)}>{editing ? "Cancel" : "Edit"}</Button> : null}</CardHeader>
          <CardContent>
            {editing ? (
              <ClientForm defaultValues={client as unknown as Partial<ClientFormValues>} onSubmit={(v) => update.mutate(v)} submitting={update.isPending} />
            ) : (
              <dl className="grid grid-cols-2 gap-3 text-sm">
                <dt className="text-slate-500">Channel</dt><dd>{client.channel.replace(/_/g, " ")}</dd>
                <dt className="text-slate-500">Services</dt><dd>{client.services.join(", ").replace(/_/g, " ") || "—"}</dd>
                <dt className="text-slate-500">PEP</dt><dd>{client.is_pep ? "Yes (declared)" : "No"}</dd>
                <dt className="text-slate-500">Source of funds</dt><dd>{client.source_of_funds ?? "—"} {client.source_of_funds_verified ? "(verified)" : ""}</dd>
                <dt className="text-slate-500">Last screened</dt><dd>{formatDate(client.last_screened_at)}</dd>
                <dt className="text-slate-500">Next review</dt><dd>{formatDate(client.next_review_date)}</dd>
              </dl>
            )}
          </CardContent>
        </Card>
        <Card>
          <CardHeader><CardTitle>CDD checklist</CardTitle></CardHeader>
          <CardContent className="space-y-3 text-sm">
            {cdd.missing_fields.length ? <Alert tone="warning" title="Missing information">{cdd.missing_fields.join(", ").replace(/_/g, " ")}</Alert> : null}
            <p className="text-slate-600">Verify with one of: {cdd.verify_with_one_of.map((s) => s.join(" + ").replace(/_/g, " ")).join(" · or ")}</p>
            <p className="text-slate-600">Documents on file: {cdd.documents_present.join(", ").replace(/_/g, " ") || "none"}</p>
            <div className="space-y-2">{cdd.checklist.map((item) => <Checkbox key={item} label={item} checked={!!checked[item]} onChange={(e) => setChecked({ ...checked, [item]: e.target.checked })} />)}</div>
            {can("client:update") ? <Button size="sm" onClick={() => verify.mutate()} loading={verify.isPending}>Record verification</Button> : null}
            {cdd.verifications.length ? <p className="text-xs text-slate-500">{cdd.verifications.length} verification record(s); latest: {cdd.verifications[0].result}</p> : null}
            <p className="text-xs text-slate-400">Electronic verification providers can be connected later (Firm admin → Integrations).</p>
          </CardContent>
        </Card>
        <Comments resourceType="client" resourceId={clientId} />
      </div>
      <Card className="h-fit">
        <CardHeader><CardTitle>Decision</CardTitle></CardHeader>
        <CardContent className="space-y-2">
          {client.status === "pending" ? (
            <>
              {can("risk:approve") ? <Button className="w-full" onClick={() => action.mutate("approve")} loading={action.isPending}>Approve client</Button> : null}
              {can("client:update") ? <Button className="w-full" variant="secondary" onClick={() => action.mutate("request-approval")}>Request approval</Button> : null}
              {can("client:update") ? <Button className="w-full" variant="destructive" onClick={() => action.mutate("decline")}>Decline</Button> : null}
            </>
          ) : null}
          {client.status === "approved" && can("client:update") ? (
            <>
              <Button className="w-full" variant="secondary" onClick={() => action.mutate("review-complete")}>Mark review complete</Button>
              <Button className="w-full" variant="destructive" onClick={() => action.mutate("exit")}>Exit client</Button>
            </>
          ) : null}
          {action.error ? <Alert tone="danger">{(action.error as Error).message}</Alert> : null}
          <p className="text-xs text-slate-500">High-risk clients need a second person to approve (four-eyes) and completed enhanced due diligence.</p>
        </CardContent>
      </Card>
    </div>
  );
}
