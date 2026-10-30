"use client";
import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Alert, Badge, Button, Card, CardContent, CardHeader, CardTitle, Field, Input, PageHeader, Table, TBody, TD, TH, THead, TR, Textarea } from "@complymate/ui";
import { get, post } from "@/lib/api-client";

interface Session { id: string; tenant_id: string; reason: string; duration_minutes: number; consented_at: string | null; expires_at: string | null; ended_at: string | null; created_at: string }

export default function ImpersonationPage() {
  const qc = useQueryClient();
  const { data = [] } = useQuery({ queryKey: ["imp"], queryFn: () => get<Session[]>("/platform/impersonation"), refetchInterval: 15_000 });
  const [form, setForm] = useState({ tenant_id: "", reason: "", minutes: 30 });
  const request = useMutation({ mutationFn: () => post("/platform/impersonation", form), onSuccess: () => void qc.invalidateQueries({ queryKey: ["imp"] }) });
  const active = (s: Session) => s.consented_at && !s.ended_at && s.expires_at && new Date(s.expires_at) > new Date();
  return (
    <>
      <PageHeader title="Support access" description="Read-only access to a firm, only with the owner&apos;s consent and for a limited time." />
      <Alert tone="warning" className="mb-6">Every request, approval and page you open is recorded in the tenant&apos;s and the platform&apos;s audit logs. ID documents and SMRs are never visible.</Alert>
      <Card>
        <CardHeader><CardTitle>Request access</CardTitle></CardHeader>
        <CardContent className="grid gap-3 md:grid-cols-3">
          <Field label="Tenant id"><Input value={form.tenant_id} onChange={(e) => setForm({ ...form, tenant_id: e.target.value })} /></Field>
          <Field label="Minutes (max 60)"><Input type="number" min={1} max={60} value={form.minutes} onChange={(e) => setForm({ ...form, minutes: Number(e.target.value) })} /></Field>
          <Field label="Reason (shown to the firm owner)"><Textarea rows={2} value={form.reason} onChange={(e) => setForm({ ...form, reason: e.target.value })} /></Field>
          <div><Button onClick={() => request.mutate()} disabled={!form.tenant_id || form.reason.length < 10} loading={request.isPending}>Send request</Button></div>
          {request.error ? <Alert tone="danger" className="md:col-span-3">{(request.error as Error).message}</Alert> : null}
        </CardContent>
      </Card>
      <Card className="mt-6">
        <CardContent className="pt-5">
          <Table>
            <THead><TR><TH>Tenant</TH><TH>Reason</TH><TH>Status</TH><TH /></TR></THead>
            <TBody>{data.map((s) => (
              <TR key={s.id}>
                <TD className="font-mono text-xs">{s.tenant_id}</TD><TD>{s.reason}</TD>
                <TD>{active(s) ? <Badge tone="success">Active until {new Date(s.expires_at!).toLocaleTimeString("en-AU")}</Badge> : s.ended_at ? <Badge>Ended</Badge> : s.consented_at ? <Badge>Expired</Badge> : <Badge tone="warning">Awaiting consent</Badge>}</TD>
                <TD className="space-x-1 text-right">
                  {active(s) ? (
                    <>
                      <Button size="sm" variant="secondary" onClick={() => navigator.clipboard.writeText(s.id)}>Copy session id</Button>
                      <Button size="sm" variant="ghost" onClick={async () => { await post(`/platform/impersonation/${s.id}/end`); void qc.invalidateQueries({ queryKey: ["imp"] }); }}>End</Button>
                    </>
                  ) : null}
                </TD>
              </TR>
            ))}</TBody>
          </Table>
          <p className="mt-2 text-xs text-slate-500">Open the tenant app and send header X-Impersonation-Id with the session id (support tooling sets this automatically).</p>
        </CardContent>
      </Card>
    </>
  );
}
