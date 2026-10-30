"use client";
import { useEffect, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Alert, Button, Card, CardContent, CardHeader, CardTitle, Checkbox, Field, Input, Table, TBody, TD, TH, THead, TR, Textarea } from "@complymate/ui";
import { get, post } from "@/lib/api-client";
import { formatDateTime } from "@/lib/format";
import { useSettings } from "../_settings";

interface Imp { id: string; reason: string; duration_minutes: number; consented_at: string | null; expires_at: string | null; ended_at: string | null; created_at: string }

export default function SecurityPage() {
  const qc = useQueryClient();
  const { settings, save } = useSettings();
  const [form, setForm] = useState({ mfa_required: true, session_timeout_minutes: 30, ip_allow_list: "", allow_support_impersonation: false });
  const { data: requests = [] } = useQuery({ queryKey: ["imp"], queryFn: () => get<Imp[]>("/tenants/current/impersonation-requests") });
  useEffect(() => {
    if (settings) setForm({ mfa_required: settings.mfa_required, session_timeout_minutes: settings.session_timeout_minutes, ip_allow_list: settings.ip_allow_list.join("\n"), allow_support_impersonation: settings.allow_support_impersonation });
  }, [settings]);
  return (
    <div className="space-y-6">
      <Card>
        <CardHeader><CardTitle>Sign-in security</CardTitle></CardHeader>
        <CardContent className="grid gap-4 md:grid-cols-2">
          <Checkbox label="Require MFA for everyone (recommended)" checked={form.mfa_required} onChange={(e) => setForm({ ...form, mfa_required: e.target.checked })} />
          <Field label="Idle session timeout (minutes)"><Input type="number" min={5} max={720} value={form.session_timeout_minutes} onChange={(e) => setForm({ ...form, session_timeout_minutes: Number(e.target.value) })} /></Field>
          <Field label="IP allow-list (Practice plan)" hint="One CIDR per line, e.g. 203.0.113.0/24. Leave empty to allow any network."><Textarea value={form.ip_allow_list} onChange={(e) => setForm({ ...form, ip_allow_list: e.target.value })} /></Field>
          <Checkbox label="Allow ComplyMate support to request temporary read-only access" checked={form.allow_support_impersonation} onChange={(e) => setForm({ ...form, allow_support_impersonation: e.target.checked })} />
          <div className="md:col-span-2">
            <Button loading={save.isPending} onClick={() => save.mutate({ ...form, ip_allow_list: form.ip_allow_list.split("\n").map((s) => s.trim()).filter(Boolean) })}>Save security settings</Button>
            {save.error ? <Alert tone="danger" className="mt-2">{(save.error as Error).message}</Alert> : null}
          </div>
        </CardContent>
      </Card>
      <Card>
        <CardHeader><CardTitle>Support access requests</CardTitle></CardHeader>
        <CardContent>
          <Table>
            <THead><TR><TH>Requested</TH><TH>Reason</TH><TH>Duration</TH><TH>Status</TH><TH /></TR></THead>
            <TBody>
              {requests.map((r) => (
                <TR key={r.id}>
                  <TD>{formatDateTime(r.created_at)}</TD><TD>{r.reason}</TD><TD>{r.duration_minutes} min</TD>
                  <TD>{r.ended_at ? "Ended/declined" : r.consented_at ? `Active until ${formatDateTime(r.expires_at)}` : "Awaiting your decision"}</TD>
                  <TD className="space-x-1 text-right">
                    {!r.consented_at && !r.ended_at ? (
                      <>
                        <Button size="sm" onClick={async () => { await post(`/tenants/current/impersonation-requests/${r.id}/consent`, { approve: true }); void qc.invalidateQueries({ queryKey: ["imp"] }); }}>Approve</Button>
                        <Button size="sm" variant="secondary" onClick={async () => { await post(`/tenants/current/impersonation-requests/${r.id}/consent`, { approve: false }); void qc.invalidateQueries({ queryKey: ["imp"] }); }}>Decline</Button>
                      </>
                    ) : null}
                  </TD>
                </TR>
              ))}
            </TBody>
          </Table>
          <p className="mt-2 text-xs text-slate-500">Support staff never see client ID documents or suspicious matter reports, even with access.</p>
        </CardContent>
      </Card>
    </div>
  );
}
