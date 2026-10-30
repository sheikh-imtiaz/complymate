"use client";
import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import type { KbSource } from "@complymate/api-types";
import { Alert, Badge, Button, Card, CardContent, CardHeader, CardTitle, Field, Input, PageHeader, Select, Table, TBody, TD, TH, THead, TR, Textarea } from "@complymate/ui";
import { get, patch, post } from "@/lib/api-client";

export default function KnowledgeBasePage() {
  const qc = useQueryClient();
  const { data = [] } = useQuery({ queryKey: ["kb"], queryFn: () => get<KbSource[]>("/platform/kb/sources") });
  const [form, setForm] = useState({ jurisdiction: "AU", title: "", url: "", publisher: "AUSTRAC", content: "" });
  const refresh = () => void qc.invalidateQueries({ queryKey: ["kb"] });
  const add = useMutation({ mutationFn: () => post("/platform/kb/sources", form), onSuccess: () => { setForm({ ...form, title: "", url: "", content: "" }); refresh(); } });
  const stale = (d: string | null) => !d || Date.now() - new Date(d).getTime() > 90 * 86400_000;
  return (
    <>
      <PageHeader title="Rule library" description="Regulator guidance the agent answers from. Keep 'last checked' current — users see it on every citation." />
      <Card>
        <CardContent className="pt-5">
          <Table>
            <THead><TR><TH>Source</TH><TH>Jurisdiction</TH><TH>Chunks</TH><TH>Last checked</TH><TH /></TR></THead>
            <TBody>
              {data.map((s) => (
                <TR key={s.id}>
                  <TD>{s.title}<br /><span className="text-xs text-slate-500">{s.publisher}{s.status !== "active" ? " · archived" : ""}</span></TD>
                  <TD>{s.jurisdiction}</TD><TD>{s.chunk_count}</TD>
                  <TD>{s.last_checked_at ? new Date(s.last_checked_at).toLocaleDateString("en-AU") : "—"} {stale(s.last_checked_at) ? <Badge tone="warning">check</Badge> : null}</TD>
                  <TD className="space-x-1 text-right">
                    <Button size="sm" variant="ghost" onClick={async () => { await patch(`/platform/kb/sources/${s.id}/last-checked`, {}); refresh(); }}>Mark checked today</Button>
                    <Button size="sm" variant="ghost" onClick={async () => { await post(`/platform/kb/sources/${s.id}/reindex`); refresh(); }}>Re-index</Button>
                    <Button size="sm" variant="ghost" onClick={async () => { await post(`/platform/kb/sources/${s.id}/archive`); refresh(); }}>Archive</Button>
                  </TD>
                </TR>
              ))}
            </TBody>
          </Table>
        </CardContent>
      </Card>
      <Card className="mt-6">
        <CardHeader><CardTitle>Add a source document</CardTitle></CardHeader>
        <CardContent className="grid gap-3">
          <div className="grid gap-3 md:grid-cols-4">
            <Field label="Jurisdiction"><Select value={form.jurisdiction} onChange={(e) => setForm({ ...form, jurisdiction: e.target.value })}><option>AU</option><option>NZ</option></Select></Field>
            <Field label="Publisher"><Input value={form.publisher} onChange={(e) => setForm({ ...form, publisher: e.target.value })} /></Field>
            <Field label="Title"><Input value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} /></Field>
            <Field label="URL"><Input value={form.url} onChange={(e) => setForm({ ...form, url: e.target.value })} /></Field>
          </div>
          <Field label="Content (Markdown or plain text, headings help chunking)"><Textarea rows={10} value={form.content} onChange={(e) => setForm({ ...form, content: e.target.value })} /></Field>
          <div><Button onClick={() => add.mutate()} disabled={!form.title || form.content.length < 50} loading={add.isPending}>Upload and index</Button></div>
          {add.error ? <Alert tone="danger">{(add.error as Error).message}</Alert> : null}
        </CardContent>
      </Card>
    </>
  );
}
