"use client";
import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import type { Role } from "@complymate/api-types";
import { Alert, Badge, Button, Card, CardContent, CardHeader, CardTitle, Field, Input, Select } from "@complymate/ui";
import { del, get, post } from "@/lib/api-client";
import { usePermissions } from "@/hooks/usePermission";

export default function RolesPage() {
  const qc = useQueryClient();
  const can = usePermissions();
  const { data: roles = [] } = useQuery({ queryKey: ["roles"], queryFn: () => get<Role[]>("/roles") });
  const { data: catalog = [] } = useQuery({ queryKey: ["permission-catalog"], queryFn: () => get<string[]>("/roles/permissions") });
  const [form, setForm] = useState({ key: "", name: "", base_role_key: "staff", permissions: [] as string[] });
  const create = useMutation({ mutationFn: () => post("/roles", form), onSuccess: () => void qc.invalidateQueries({ queryKey: ["roles"] }) });
  return (
    <div className="space-y-6">
      <div className="grid gap-4 md:grid-cols-2">
        {roles.map((r) => (
          <Card key={r.id}>
            <CardHeader className="flex-row items-center justify-between">
              <CardTitle>{r.name}</CardTitle>
              <div className="flex items-center gap-2">{r.is_system ? <Badge>System</Badge> : <Badge tone="info">Custom</Badge>}
                {!r.is_system && can("user:delete") ? <Button size="sm" variant="ghost" onClick={async () => { await del(`/roles/${r.id}`); void qc.invalidateQueries({ queryKey: ["roles"] }); }}>Delete</Button> : null}</div>
            </CardHeader>
            <CardContent>
              <p className="mb-2 text-sm text-slate-500">{r.description}</p>
              <div className="flex flex-wrap gap-1">{r.permissions.map((p) => <code key={p} className="rounded bg-slate-100 px-1.5 py-0.5 text-[11px]">{p}</code>)}</div>
            </CardContent>
          </Card>
        ))}
      </div>
      {can("user:create") ? (
        <Card>
          <CardHeader><CardTitle>Create a custom role (Practice plan)</CardTitle></CardHeader>
          <CardContent className="space-y-3">
            <div className="grid gap-3 md:grid-cols-3">
              <Field label="Key" hint="lowercase, e.g. bookkeeper"><Input value={form.key} onChange={(e) => setForm({ ...form, key: e.target.value })} /></Field>
              <Field label="Name"><Input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} /></Field>
              <Field label="Based on">
                <Select value={form.base_role_key} onChange={(e) => setForm({ ...form, base_role_key: e.target.value, permissions: roles.find((r) => r.key === e.target.value)?.permissions ?? [] })}>
                  {roles.filter((r) => r.is_system).map((r) => <option key={r.key} value={r.key}>{r.name}</option>)}
                </Select>
              </Field>
            </div>
            <div className="grid max-h-64 grid-cols-2 gap-1 overflow-y-auto rounded border p-2 md:grid-cols-4">
              {catalog.map((p) => (
                <label key={p} className="flex items-center gap-1 text-xs">
                  <input type="checkbox" checked={form.permissions.includes(p)} onChange={(e) => setForm({ ...form, permissions: e.target.checked ? [...form.permissions, p] : form.permissions.filter((x) => x !== p) })} />{p}
                </label>
              ))}
            </div>
            <Button onClick={() => create.mutate()} disabled={!form.key || !form.name} loading={create.isPending}>Create role</Button>
            {create.error ? <Alert tone="danger">{(create.error as Error).message}</Alert> : null}
          </CardContent>
        </Card>
      ) : null}
    </div>
  );
}
