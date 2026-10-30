"use client";
import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import type { Invitation, Member, Role } from "@complymate/api-types";
import { Alert, Badge, Button, Card, CardContent, CardHeader, CardTitle, Field, Input, Select, Table, TBody, TD, TH, THead, TR } from "@complymate/ui";
import { del, get, patch, post } from "@/lib/api-client";
import { formatDate, humanize } from "@/lib/format";
import { usePermissions } from "@/hooks/usePermission";
import { useTenant } from "@/hooks/useTenant";

export default function UsersPage() {
  const qc = useQueryClient();
  const can = usePermissions();
  const { me } = useTenant();
  const { data: users = [] } = useQuery({ queryKey: ["users"], queryFn: () => get<Member[]>("/users") });
  const { data: roles = [] } = useQuery({ queryKey: ["roles"], queryFn: () => get<Role[]>("/roles") });
  const { data: invites = [] } = useQuery({ queryKey: ["invitations"], queryFn: () => get<Invitation[]>("/invitations") });
  const { data: tenant } = useQuery({ queryKey: ["tenant"], queryFn: () => get<{ amlco_user_id: string | null }>("/tenants/current") });
  const [invite, setInvite] = useState({ email: "", full_name: "", role_key: "staff" });
  const [msg, setMsg] = useState<string | null>(null);
  const refresh = () => ["users", "invitations", "tenant"].forEach((k) => void qc.invalidateQueries({ queryKey: [k] }));
  const run = useMutation({
    mutationFn: async (fn: () => Promise<unknown>) => fn(),
    onSuccess: () => { setMsg(null); refresh(); },
    onError: (e) => setMsg((e as Error).message),
  });
  return (
    <div className="space-y-6">
      {!tenant?.amlco_user_id ? <Alert tone="warning" title="Nominate your AML/CTF compliance officer">Choose a team member below and click “Make AMLCO”.</Alert> : null}
      {msg ? <Alert tone="danger">{msg}</Alert> : null}
      <Card>
        <CardHeader><CardTitle>Team</CardTitle></CardHeader>
        <CardContent>
          <Table>
            <THead><TR><TH>Name</TH><TH>Role</TH><TH>MFA</TH><TH>Last sign-in</TH><TH>Status</TH><TH /></TR></THead>
            <TBody>
              {users.map((u) => (
                <TR key={u.user_id}>
                  <TD>{u.full_name ?? u.email}<br /><span className="text-xs text-slate-500">{u.email}</span>{tenant?.amlco_user_id === u.user_id ? <Badge tone="info" className="ml-2">AMLCO</Badge> : null}</TD>
                  <TD>
                    {can("user:update") && u.user_id !== me?.user_id ? (
                      <Select value={u.role_key} onChange={(e) => run.mutate(() => patch(`/users/${u.user_id}/role`, { role_key: e.target.value }))} className="w-44">
                        {roles.map((r) => <option key={r.id} value={r.key}>{r.name}</option>)}
                      </Select>
                    ) : humanize(u.role_key)}
                  </TD>
                  <TD>{u.mfa_enrolled ? <Badge tone="success">On</Badge> : <Badge tone="warning">Pending</Badge>}</TD>
                  <TD>{formatDate(u.last_login_at)}</TD>
                  <TD><Badge tone={u.status === "active" ? "success" : "neutral"}>{u.status}</Badge></TD>
                  <TD className="space-x-1 text-right">
                    {can("firm:update") && tenant?.amlco_user_id !== u.user_id ? <Button size="sm" variant="ghost" onClick={() => run.mutate(() => post("/tenants/current/amlco", { user_id: u.user_id }))}>Make AMLCO</Button> : null}
                    {can("user:update") ? <Button size="sm" variant="ghost" onClick={() => run.mutate(() => post(`/users/${u.user_id}/reset-mfa`))}>Reset MFA</Button> : null}
                    {can("user:delete") && u.user_id !== me?.user_id ? (
                      u.status === "active"
                        ? <Button size="sm" variant="ghost" onClick={() => run.mutate(() => post(`/users/${u.user_id}/deactivate`))}>Deactivate</Button>
                        : <Button size="sm" variant="ghost" onClick={() => run.mutate(() => post(`/users/${u.user_id}/reactivate`))}>Reactivate</Button>
                    ) : null}
                  </TD>
                </TR>
              ))}
            </TBody>
          </Table>
        </CardContent>
      </Card>
      {can("user:create") ? (
        <Card>
          <CardHeader><CardTitle>Invite a team member</CardTitle></CardHeader>
          <CardContent className="grid gap-3 md:grid-cols-4">
            <Field label="Email"><Input type="email" value={invite.email} onChange={(e) => setInvite({ ...invite, email: e.target.value })} /></Field>
            <Field label="Name"><Input value={invite.full_name} onChange={(e) => setInvite({ ...invite, full_name: e.target.value })} /></Field>
            <Field label="Role">
              <Select value={invite.role_key} onChange={(e) => setInvite({ ...invite, role_key: e.target.value })}>
                {roles.filter((r) => r.key !== "advisor").map((r) => <option key={r.id} value={r.key}>{r.name}</option>)}
              </Select>
            </Field>
            <div className="flex items-end"><Button disabled={!invite.email} onClick={() => run.mutate(async () => { await post("/invitations", invite); setInvite({ email: "", full_name: "", role_key: "staff" }); })}>Send invitation</Button></div>
          </CardContent>
        </Card>
      ) : null}
      {invites.filter((i) => !i.accepted_at && !i.revoked_at).length ? (
        <Card>
          <CardHeader><CardTitle>Pending invitations</CardTitle></CardHeader>
          <CardContent>
            <Table>
              <THead><TR><TH>Email</TH><TH>Expires</TH><TH /></TR></THead>
              <TBody>{invites.filter((i) => !i.accepted_at && !i.revoked_at).map((i) => (
                <TR key={i.id}><TD>{i.email}</TD><TD>{formatDate(i.expires_at)}</TD><TD className="text-right"><Button size="sm" variant="ghost" onClick={() => run.mutate(() => del(`/invitations/${i.id}`))}>Revoke</Button></TD></TR>
              ))}</TBody>
            </Table>
          </CardContent>
        </Card>
      ) : null}
    </div>
  );
}
