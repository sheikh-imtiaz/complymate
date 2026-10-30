"use client";
import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import type { Interview } from "@complymate/api-types";
import { Button, Card, CardContent, Field, Input, Select, Spinner, Textarea } from "@complymate/ui";
import { get, put } from "@/lib/api-client";

const PAGE_SIZE = 4;

/** Guided interview (24 questions), saved as you go (debounced autosave on every change). */
export function InterviewWizard({ onFinished }: { onFinished?: () => void }) {
  const qc = useQueryClient();
  const { data } = useQuery({ queryKey: ["interview"], queryFn: () => get<Interview>("/program/interview") });
  const [answers, setAnswers] = useState<Record<string, unknown>>({});
  const [page, setPage] = useState(0);
  const [dirty, setDirty] = useState<Record<string, unknown>>({});
  useEffect(() => {
    if (data) setAnswers(data.answers ?? {});
  }, [data]);

  const save = useMutation({
    mutationFn: (changes: Record<string, unknown>) => put<Interview>("/program/interview", { answers: changes }),
    onSuccess: (res) => qc.setQueryData(["interview"], res),
  });

  useEffect(() => {
    if (!Object.keys(dirty).length) return;
    const t = setTimeout(() => {
      save.mutate(dirty);
      setDirty({});
    }, 800);
    return () => clearTimeout(t);
  }, [dirty, save]);

  const questions = useMemo(() => data?.questions ?? [], [data]);
  const pages = Math.ceil(questions.length / PAGE_SIZE);
  const current = useMemo(() => questions.slice(page * PAGE_SIZE, page * PAGE_SIZE + PAGE_SIZE), [questions, page]);
  if (!data) return <Spinner />;

  const set = (id: string, value: unknown) => {
    setAnswers((a) => ({ ...a, [id]: value }));
    setDirty((d) => ({ ...d, [id]: value }));
  };

  return (
    <Card>
      <CardContent className="space-y-5 pt-5">
        <div className="flex items-center justify-between text-sm text-slate-500">
          <span>Step {page + 1} of {pages}</span>
          <span>{Math.round((data.progress ?? 0) * 100)}% answered {save.isPending ? "· saving…" : "· saved"}</span>
        </div>
        <div className="h-1.5 w-full overflow-hidden rounded bg-slate-100">
          <div className="h-full bg-brand-600 transition-all" style={{ width: `${(data.progress ?? 0) * 100}%` }} />
        </div>
        {current.map((q) => (
          <Field key={q.id} label={q.text} hint={q.help || undefined}>
            {q.kind === "yesno" ? (
              <Select value={String(answers[q.id] ?? "")} onChange={(e) => set(q.id, e.target.value === "" ? null : e.target.value === "true")}>
                <option value="">Choose…</option>
                <option value="true">Yes</option>
                <option value="false">No</option>
              </Select>
            ) : q.kind === "choice" ? (
              <Select value={String(answers[q.id] ?? "")} onChange={(e) => set(q.id, e.target.value)}>
                <option value="">Choose…</option>
                {q.options.map((o) => <option key={o} value={o}>{o}</option>)}
              </Select>
            ) : q.kind === "multichoice" ? (
              <div className="grid gap-1.5 md:grid-cols-2">
                {q.options.map((o) => {
                  const selected = (answers[q.id] as string[] | undefined) ?? [];
                  return (
                    <label key={o} className="flex items-center gap-2 text-sm">
                      <input
                        type="checkbox"
                        checked={selected.includes(o)}
                        onChange={(e) => set(q.id, e.target.checked ? [...selected, o] : selected.filter((x) => x !== o))}
                      />
                      {o.replace(/_/g, " ")}
                    </label>
                  );
                })}
              </div>
            ) : q.kind === "number" ? (
              <Input type="number" value={String(answers[q.id] ?? "")} onChange={(e) => set(q.id, e.target.value ? Number(e.target.value) : null)} />
            ) : (
              <Textarea value={String(answers[q.id] ?? "")} onChange={(e) => set(q.id, e.target.value)} rows={3} />
            )}
          </Field>
        ))}
        <div className="flex justify-between">
          <Button variant="secondary" disabled={page === 0} onClick={() => setPage((p) => p - 1)}>Back</Button>
          {page < pages - 1 ? (
            <Button onClick={() => setPage((p) => p + 1)}>Next</Button>
          ) : (
            <Button onClick={onFinished}>Finish</Button>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
