"use client";
import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import type { QuizQuestion, TrainingModule } from "@complymate/api-types";
import { Alert, Badge, Button, Card, CardContent, PageHeader, Select } from "@complymate/ui";
import { get, patch, post } from "@/lib/api-client";

export default function QuizzesPage() {
  const qc = useQueryClient();
  const { data: modules = [] } = useQuery({ queryKey: ["templates"], queryFn: () => get<TrainingModule[]>("/platform/templates") });
  const [moduleId, setModuleId] = useState("");
  const [status, setStatus] = useState("draft");
  const qs = new URLSearchParams({ ...(moduleId && { module_id: moduleId }), ...(status && { review_status: status }) });
  const { data = [] } = useQuery({ queryKey: ["quizzes", moduleId, status], queryFn: () => get<QuizQuestion[]>(`/platform/quizzes?${qs}`) });
  const refresh = () => void qc.invalidateQueries({ queryKey: ["quizzes"] });
  const generate = useMutation({ mutationFn: () => post("/platform/quizzes/generate", { module_id: moduleId, count: 5 }), onSuccess: refresh });
  return (
    <>
      <PageHeader title="Quiz review" description="Agent-generated questions start as drafts. Approve only what is accurate and sourced."
        actions={<Button disabled={!moduleId} onClick={() => generate.mutate()} loading={generate.isPending}>Generate 5 questions</Button>} />
      <div className="mb-4 flex gap-3">
        <Select value={moduleId} onChange={(e) => setModuleId(e.target.value)} className="w-72" aria-label="Module"><option value="">All modules</option>{modules.map((m) => <option key={m.id} value={m.id}>{m.title}</option>)}</Select>
        <Select value={status} onChange={(e) => setStatus(e.target.value)} className="w-40" aria-label="Status"><option value="draft">Draft</option><option value="approved">Approved</option><option value="rejected">Rejected</option></Select>
      </div>
      {generate.error ? <Alert tone="danger" className="mb-4">{(generate.error as Error).message}</Alert> : null}
      <div className="space-y-3">
        {data.map((q) => (
          <Card key={q.id}>
            <CardContent className="space-y-2 pt-5 text-sm">
              <div className="flex items-center gap-2"><p className="font-medium">{q.question}</p>{q.ai_generated ? <Badge tone="info">AI</Badge> : null}</div>
              <ol className="list-decimal pl-5">{q.options.map((o, i) => <li key={o} className={i === q.correct_index ? "font-semibold text-risk-low" : ""}>{o}</li>)}</ol>
              {q.explanation ? <p className="text-slate-500">{q.explanation}</p> : null}
              {q.source_citation ? <p className="text-xs text-slate-400">Source: {String(q.source_citation.title)}</p> : null}
              {q.review_status === "draft" ? (
                <div className="flex gap-2">
                  <Button size="sm" onClick={async () => { await patch(`/platform/quizzes/${q.id}`, { review_status: "approved" }); refresh(); }}>Approve</Button>
                  <Button size="sm" variant="secondary" onClick={async () => { await patch(`/platform/quizzes/${q.id}`, { review_status: "rejected" }); refresh(); }}>Reject</Button>
                </div>
              ) : null}
            </CardContent>
          </Card>
        ))}
      </div>
    </>
  );
}
