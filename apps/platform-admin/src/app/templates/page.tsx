"use client";
import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import type { TrainingModule } from "@complymate/api-types";
import { Alert, Badge, Button, Card, CardContent, CardHeader, CardTitle, Field, Input, PageHeader, Select, Table, TBody, TD, TH, THead, TR, Textarea } from "@complymate/ui";
import { get, post, put } from "@/lib/api-client";

const EMPTY = { title: "", description: "", content_md: "", roles: ["staff"], jurisdiction: "AU", duration_minutes: 15, pass_mark: 80, status: "draft" };

export default function TemplatesPage() {
  const qc = useQueryClient();
  const { data = [] } = useQuery({ queryKey: ["templates"], queryFn: () => get<TrainingModule[]>("/platform/templates") });
  const [form, setForm] = useState(EMPTY);
  const [editId, setEditId] = useState<string | null>(null);
  const save = useMutation({
    mutationFn: () => (editId ? put(`/platform/templates/${editId}`, form) : post("/platform/templates", form)),
    onSuccess: () => { setForm(EMPTY); setEditId(null); void qc.invalidateQueries({ queryKey: ["templates"] }); },
  });
  return (
    <>
      <PageHeader title="Training templates" description="Platform training modules shared with every firm once published." />
      <Card>
        <CardContent className="pt-5">
          <Table>
            <THead><TR><TH>Module</TH><TH>Jurisdiction</TH><TH>Status</TH><TH>Version</TH><TH /></TR></THead>
            <TBody>{data.map((m) => (
              <TR key={m.id}>
                <TD>{m.title}</TD><TD>{m.jurisdiction}</TD><TD><Badge tone={m.status === "published" ? "success" : "neutral"}>{m.status}</Badge></TD><TD>{m.version}</TD>
                <TD className="text-right"><Button size="sm" variant="ghost" onClick={() => { setEditId(m.id); setForm({ ...EMPTY, ...m, description: m.description ?? "", content_md: "" }); }}>Edit</Button></TD>
              </TR>
            ))}</TBody>
          </Table>
        </CardContent>
      </Card>
      <Card className="mt-6">
        <CardHeader><CardTitle>{editId ? "Edit module" : "New module"}</CardTitle></CardHeader>
        <CardContent className="grid gap-3">
          <div className="grid gap-3 md:grid-cols-4">
            <Field label="Title"><Input value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} /></Field>
            <Field label="Jurisdiction"><Select value={form.jurisdiction} onChange={(e) => setForm({ ...form, jurisdiction: e.target.value })}><option>AU</option><option>NZ</option></Select></Field>
            <Field label="Minutes"><Input type="number" value={form.duration_minutes} onChange={(e) => setForm({ ...form, duration_minutes: Number(e.target.value) })} /></Field>
            <Field label="Status"><Select value={form.status} onChange={(e) => setForm({ ...form, status: e.target.value })}><option value="draft">Draft</option><option value="in_review">In review</option><option value="published">Published</option></Select></Field>
          </div>
          <Field label="Description"><Input value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} /></Field>
          <Field label="Content (Markdown)"><Textarea rows={8} value={form.content_md} onChange={(e) => setForm({ ...form, content_md: e.target.value })} /></Field>
          <div><Button onClick={() => save.mutate()} disabled={form.title.length < 3} loading={save.isPending}>Save</Button></div>
          {save.error ? <Alert tone="danger">{(save.error as Error).message}</Alert> : null}
        </CardContent>
      </Card>
    </>
  );
}
