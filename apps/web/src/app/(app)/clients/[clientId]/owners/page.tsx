"use client";
import { use, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import type { Party } from "@complymate/api-types";
import { Button, Card, CardContent, CardHeader, CardTitle, Checkbox, Field, Input, Select, Table, TBody, TD, TH, THead, TR } from "@complymate/ui";
import { OwnershipTree, type TreeNode } from "@/components/clients/OwnershipTree";
import { del, get, post } from "@/lib/api-client";
import { usePermissions } from "@/hooks/usePermission";

interface TreeData { root: { name: string; client_type: string }; tree: TreeNode[]; beneficial_owners: { name: string; effective_percent: number; control: boolean; is_pep: boolean }[] }
const EMPTY = { full_name: "", party_type: "beneficial_owner", is_entity: false, ownership_percent: "", parent_party_id: "", country: "", date_of_birth: "", is_pep: false, has_control: false };

export default function OwnersPage({ params }: { params: Promise<{ clientId: string }> }) {
  const { clientId } = use(params);
  const qc = useQueryClient();
  const can = usePermissions();
  const { data: parties = [] } = useQuery({ queryKey: ["parties", clientId], queryFn: () => get<Party[]>(`/clients/${clientId}/parties`) });
  const { data: tree } = useQuery({ queryKey: ["tree", clientId], queryFn: () => get<TreeData>(`/clients/${clientId}/ownership-tree`) });
  const [form, setForm] = useState(EMPTY);
  const refresh = () => ["parties", "tree"].forEach((k) => void qc.invalidateQueries({ queryKey: [k, clientId] }));
  const add = useMutation({
    mutationFn: () => post(`/clients/${clientId}/parties`, {
      ...form, ownership_percent: form.ownership_percent ? Number(form.ownership_percent) : null, parent_party_id: form.parent_party_id || null,
      country: form.country || null, date_of_birth: form.date_of_birth || null,
    }),
    onSuccess: () => { setForm(EMPTY); refresh(); },
  });
  return (
    <div className="grid gap-6 lg:grid-cols-2">
      <Card>
        <CardHeader><CardTitle>Ownership and control</CardTitle></CardHeader>
        <CardContent className="space-y-4">
          {tree ? <OwnershipTree root={tree.root} tree={tree.tree} /> : null}
          <div className="rounded-lg bg-slate-50 p-3 text-sm">
            <p className="font-medium">Beneficial owners (25% or more, or control)</p>
            {tree?.beneficial_owners.length ? (
              <ul className="mt-1 list-disc pl-5">{tree.beneficial_owners.map((b) => <li key={b.name}>{b.name} — {b.effective_percent}%{b.control ? " · control" : ""}{b.is_pep ? " · PEP" : ""}</li>)}</ul>
            ) : <p className="text-slate-500">None identified yet.</p>}
          </div>
          <Table>
            <THead><TR><TH>Name</TH><TH>Role</TH><TH>%</TH><TH /></TR></THead>
            <TBody>
              {parties.map((p) => (
                <TR key={p.id}>
                  <TD>{p.full_name}</TD><TD>{p.party_type.replace(/_/g, " ")}</TD><TD>{p.ownership_percent ?? "—"}</TD>
                  <TD className="text-right">{can("client:update") ? <Button size="sm" variant="ghost" onClick={async () => { await del(`/clients/${clientId}/parties/${p.id}`); refresh(); }}>Remove</Button> : null}</TD>
                </TR>
              ))}
            </TBody>
          </Table>
        </CardContent>
      </Card>
      {can("client:update") ? (
        <Card>
          <CardHeader><CardTitle>Add owner, director or controller</CardTitle></CardHeader>
          <CardContent className="grid gap-3">
            <Field label="Full name"><Input value={form.full_name} onChange={(e) => setForm({ ...form, full_name: e.target.value })} /></Field>
            <div className="grid grid-cols-2 gap-3">
              <Field label="Role">
                <Select value={form.party_type} onChange={(e) => setForm({ ...form, party_type: e.target.value })}>
                  {["beneficial_owner", "director", "shareholder_entity", "trustee", "settlor", "beneficiary", "appointor", "protector", "partner"].map((t) => <option key={t} value={t}>{t.replace(/_/g, " ")}</option>)}
                </Select>
              </Field>
              <Field label="Owned via (parent)">
                <Select value={form.parent_party_id} onChange={(e) => setForm({ ...form, parent_party_id: e.target.value })}>
                  <option value="">Directly</option>
                  {parties.filter((p) => p.is_entity).map((p) => <option key={p.id} value={p.id}>{p.full_name}</option>)}
                </Select>
              </Field>
              <Field label="Ownership %"><Input type="number" min={0} max={100} value={form.ownership_percent} onChange={(e) => setForm({ ...form, ownership_percent: e.target.value })} /></Field>
              <Field label="Country (ISO)"><Input maxLength={2} value={form.country} onChange={(e) => setForm({ ...form, country: e.target.value.toUpperCase() })} /></Field>
              <Field label="Date of birth"><Input type="date" value={form.date_of_birth} onChange={(e) => setForm({ ...form, date_of_birth: e.target.value })} /></Field>
            </div>
            <div className="flex flex-wrap gap-4">
              <Checkbox label="Is a company/trust" checked={form.is_entity} onChange={(e) => setForm({ ...form, is_entity: e.target.checked })} />
              <Checkbox label="Has control" checked={form.has_control} onChange={(e) => setForm({ ...form, has_control: e.target.checked })} />
              <Checkbox label="PEP" checked={form.is_pep} onChange={(e) => setForm({ ...form, is_pep: e.target.checked })} />
            </div>
            <Button onClick={() => add.mutate()} disabled={!form.full_name} loading={add.isPending}>Add</Button>
          </CardContent>
        </Card>
      ) : null}
    </div>
  );
}
