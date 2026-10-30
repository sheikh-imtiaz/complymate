"use client";
import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import type { ApiKey } from "@complymate/api-types";
import { Alert, Button, Card, CardContent, CardHeader, CardTitle, Field, Input, Table, TBody, TD, TH, THead, TR } from "@complymate/ui";
import { del, get, post } from "@/lib/api-client";
import { formatDate } from "@/lib/format";
import { usePermissions } from "@/hooks/usePermission";

const SAFE = ["client:read", "client:create", "screening:create", "screening:read", "report:read", "risk:read"];

export default function ApiKeysPage() {
  const qc = useQueryClient();
  const can = usePermissions();
  const { data = [] } = useQuery({ queryKey: ["api-keys"], queryFn: () => get<ApiKey[]>("/api-keys") });
  const [name, setName] = useState("");
  const [perms, setPerms] = useState<string[]>(["client:read"]);
  const [created, setCreated] = useState<string | null>(null);
  const create = useMutation({
    mutationFn: () => post<{ key: string }>("/api-keys", { name, permissions: perms }),
    onSuccess: (r) => { setCreated(r.key); void qc.invalidateQueries({ queryKey: ["api-keys"] }); },
  });
  return (
    <div className="space-y-6">
      {created ? <Alert tone="success" title="Copy your key now — it won't be shown again"><code className="break-all">{created}</code><p className="mt-1">Call the API at <code>/m2m/...</code> with header <code>X-API-Key</code>.</p></Alert> : null}
      {can("settings:update") ? (
        <Card>
          <CardHeader><CardTitle>Create an API key (Practice plan)</CardTitle></CardHeader>
          <CardContent className="space-y-3">
            <Field label="Name"><Input value={name} onChange={(e) => setName(e.target.value)} placeholder="Practice management sync" /></Field>
            <div className="flex flex-wrap gap-3">{SAFE.filter((p) => can(p)).map((p) => (
              <label key={p} className="flex items-center gap-1 text-sm"><input type="checkbox" checked={perms.includes(p)} onChange={(e) => setPerms(e.target.checked ? [...perms, p] : perms.filter((x) => x !== p))} />{p}</label>
            ))}</div>
            <Button disabled={!name || !perms.length} onClick={() => create.mutate()} loading={create.isPending}>Create key</Button>
            {create.error ? <Alert tone="danger">{(create.error as Error).message}</Alert> : null}
          </CardContent>
        </Card>
      ) : null}
      <Card>
        <CardHeader><CardTitle>Keys</CardTitle></CardHeader>
        <CardContent>
          <Table>
            <THead><TR><TH>Name</TH><TH>Prefix</TH><TH>Permissions</TH><TH>Last used</TH><TH /></TR></THead>
            <TBody>{data.map((k) => (
              <TR key={k.id}>
                <TD>{k.name}</TD><TD><code>{k.prefix}</code></TD><TD className="text-xs">{k.permissions.join(", ")}</TD><TD>{formatDate(k.last_used_at)}</TD>
                <TD className="text-right">{k.revoked_at ? "Revoked" : can("settings:update") ? <Button size="sm" variant="ghost" onClick={async () => { await del(`/api-keys/${k.id}`); void qc.invalidateQueries({ queryKey: ["api-keys"] }); }}>Revoke</Button> : null}</TD>
              </TR>
            ))}</TBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
}
