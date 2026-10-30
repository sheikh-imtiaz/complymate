"use client";
import { use, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import type { TrainingModuleDetail } from "@complymate/api-types";
import { Alert, Button, Card, CardContent, CardHeader, CardTitle, PageHeader, Spinner } from "@complymate/ui";
import { ReportExportButton } from "@/components/reports/ReportExportButton";
import { get, post } from "@/lib/api-client";

interface Result { attempt: { id: string; score: string; passed: boolean; certificate_key: string | null }; feedback: { question_id: string; correct: boolean; explanation: string | null }[] }

/** Module content is Markdown from the platform; rendered as plain paragraphs and lists (no raw HTML). */
function Markdown({ text }: { text: string }) {
  return (
    <div className="prose prose-sm max-w-none">
      {text.split(/\n{2,}/).map((block, i) =>
        block.startsWith("## ") ? <h3 key={i}>{block.slice(3)}</h3>
          : block.split("\n").every((l) => l.startsWith("* ")) ? <ul key={i}>{block.split("\n").map((l) => <li key={l}>{l.slice(2)}</li>)}</ul>
            : <p key={i}>{block}</p>,
      )}
    </div>
  );
}

export default function ModulePage({ params }: { params: Promise<{ moduleId: string }> }) {
  const { moduleId } = use(params);
  const { data } = useQuery({ queryKey: ["module", moduleId], queryFn: () => get<TrainingModuleDetail>(`/training/modules/${moduleId}`) });
  const [answers, setAnswers] = useState<Record<string, number>>({});
  const [result, setResult] = useState<Result | null>(null);
  if (!data) return <Spinner />;
  return (
    <>
      <PageHeader title={data.title} description={`${data.duration_minutes} minutes · pass mark ${data.pass_mark}%`} />
      <div className="space-y-6">
        <Card><CardContent className="pt-5"><Markdown text={data.content_md} /></CardContent></Card>
        <Card>
          <CardHeader><CardTitle>Quiz</CardTitle></CardHeader>
          <CardContent className="space-y-5">
            {data.questions.map((q, i) => {
              const fb = result?.feedback.find((f) => f.question_id === q.id);
              return (
                <fieldset key={q.id} className="space-y-1">
                  <legend className="font-medium">{i + 1}. {q.question}</legend>
                  {q.options.map((o, idx) => (
                    <label key={o} className="flex items-center gap-2 text-sm">
                      <input type="radio" name={q.id} checked={answers[q.id] === idx} onChange={() => setAnswers({ ...answers, [q.id]: idx })} disabled={!!result} />{o}
                    </label>
                  ))}
                  {fb ? <p className={`text-xs ${fb.correct ? "text-risk-low" : "text-risk-high"}`}>{fb.correct ? "Correct." : "Not quite."} {fb.explanation}</p> : null}
                </fieldset>
              );
            })}
            {result ? (
              <Alert tone={result.attempt.passed ? "success" : "warning"} title={`Score ${result.attempt.score}%`}>
                {result.attempt.passed ? "Well done — your certificate is ready." : "Review the module and try again."}
              </Alert>
            ) : (
              <Button disabled={Object.keys(answers).length < data.questions.length} onClick={async () => setResult(await post<Result>(`/training/modules/${moduleId}/attempts`, { answers }))}>Submit answers</Button>
            )}
            {result?.attempt.passed ? <ReportExportButton path={`/training/certificates/${result.attempt.id}`} filename="certificate.pdf" label="Download certificate" /> : null}
            {result && !result.attempt.passed ? <Button variant="secondary" onClick={() => { setResult(null); setAnswers({}); }}>Try again</Button> : null}
          </CardContent>
        </Card>
      </div>
    </>
  );
}
