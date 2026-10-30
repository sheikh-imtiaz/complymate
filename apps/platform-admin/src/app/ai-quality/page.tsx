"use client";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Badge, Button, Card, CardContent, CardHeader, CardTitle, PageHeader, Stat } from "@complymate/ui";
import { get, post } from "@/lib/api-client";

interface Quality {
  feedback_counts: Record<string, number>;
  helpful_rate: number;
  flagged: { feedback_id: string; comment: string | null; review_status: string; answer: string; model: string | null; prompt_version: string | null; created_at: string; citations: { title: string }[] }[];
  latest_eval: { score: number; min_score: number; model: string; generated_at: string; results: { id: string; passed: boolean; reasons: string[] }[] } | null;
}

export default function AiQualityPage() {
  const qc = useQueryClient();
  const { data } = useQuery({ queryKey: ["ai-quality"], queryFn: () => get<Quality>("/platform/ai-quality") });
  if (!data) return null;
  return (
    <>
      <PageHeader title="AI quality" description="User feedback on answers and nightly eval results." />
      <div className="grid gap-4 md:grid-cols-3">
        <Stat label="Helpful rate" value={`${Math.round(data.helpful_rate * 100)}%`} />
        <Stat label="Flagged wrong" value={data.feedback_counts.wrong ?? 0} tone={(data.feedback_counts.wrong ?? 0) > 0 ? "warning" : undefined} />
        <Stat label="Latest eval score" value={data.latest_eval ? `${Math.round(data.latest_eval.score * 100)}%` : "—"} hint={data.latest_eval ? `${data.latest_eval.model} · ${data.latest_eval.generated_at}` : "no run yet"} tone={data.latest_eval && data.latest_eval.score < data.latest_eval.min_score ? "danger" : "success"} />
      </div>
      {data.latest_eval ? (
        <Card className="mt-6"><CardHeader><CardTitle>Eval cases</CardTitle></CardHeader>
          <CardContent className="flex flex-wrap gap-2">{data.latest_eval.results.map((r) => <Badge key={r.id} tone={r.passed ? "success" : "danger"} title={r.reasons.join("; ")}>{r.id}</Badge>)}</CardContent>
        </Card>
      ) : null}
      <h2 className="mb-3 mt-8 text-lg font-semibold">Flagged answers</h2>
      <div className="space-y-3">
        {data.flagged.map((f) => (
          <Card key={f.feedback_id}>
            <CardContent className="space-y-2 pt-5 text-sm">
              <div className="flex items-center gap-2"><Badge tone={f.review_status === "open" ? "warning" : "success"}>{f.review_status}</Badge><span className="text-xs text-slate-500">{f.model} · prompt {f.prompt_version} · {new Date(f.created_at).toLocaleString("en-AU")}</span></div>
              {f.comment ? <p className="italic">“{f.comment}”</p> : null}
              <p className="whitespace-pre-wrap rounded bg-slate-50 p-2">{f.answer}</p>
              <p className="text-xs text-slate-500">Sources: {f.citations.map((c) => c.title).join("; ") || "none"}</p>
              {f.review_status === "open" ? <Button size="sm" onClick={async () => { await post(`/platform/ai-quality/feedback/${f.feedback_id}/resolve`, { resolution: window.prompt("Resolution (e.g. source updated, prompt fixed)") ?? "reviewed" }); void qc.invalidateQueries({ queryKey: ["ai-quality"] }); }}>Resolve</Button> : null}
            </CardContent>
          </Card>
        ))}
      </div>
    </>
  );
}
