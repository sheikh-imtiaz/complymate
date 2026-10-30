"use client";
import { useState } from "react";
import { Send, ShieldAlert } from "lucide-react";
import { Alert, Button, Card, CardContent, Spinner, Textarea } from "@complymate/ui";
import { useChatStream } from "@/hooks/useChatStream";
import { Citation } from "./Citation";
import { FeedbackButtons } from "./FeedbackButtons";

const SUGGESTIONS = [
  "When must we lodge a suspicious matter report?",
  "What counts as a beneficial owner of a trust?",
  "When do we need enhanced customer due diligence?",
  "How long must we keep CDD records?",
];

/** Renders the answer as plain text paragraphs (no HTML from the model is ever injected). */
function AnswerText({ text }: { text: string }) {
  return (
    <div className="space-y-2 whitespace-pre-wrap text-sm leading-relaxed text-slate-800">
      {text.split(/\n{2,}/).map((p, i) => <p key={i}>{p.replace(/^_|_$/g, "")}</p>)}
    </div>
  );
}

export function ChatPanel({ clientId }: { clientId?: string }) {
  const { turns, ask, busy, error, reset } = useChatStream();
  const [question, setQuestion] = useState("");

  const submit = () => {
    const q = question.trim();
    if (!q || busy) return;
    setQuestion("");
    void ask(q, clientId);
  };

  return (
    <div className="flex h-[calc(100vh-11rem)] flex-col gap-4">
      <div className="flex-1 space-y-4 overflow-y-auto pr-1">
        {turns.length === 0 ? (
          <Card>
            <CardContent className="space-y-3 pt-5">
              <p className="text-sm text-slate-600">Ask about AUSTRAC (AU) or DIA (NZ) obligations. Answers come only from the rule library and show their sources and when each was last checked.</p>
              <div className="flex flex-wrap gap-2">
                {SUGGESTIONS.map((s) => (
                  <button key={s} onClick={() => void ask(s, clientId)} className="rounded-full border border-slate-200 bg-white px-3 py-1 text-xs text-slate-700 hover:bg-slate-50">{s}</button>
                ))}
              </div>
            </CardContent>
          </Card>
        ) : null}
        {turns.map((t) =>
          t.role === "user" ? (
            <div key={t.id} className="ml-auto max-w-2xl rounded-2xl rounded-br-sm bg-brand-600 px-4 py-2 text-sm text-white">{t.content}</div>
          ) : (
            <Card key={t.id} className="max-w-3xl">
              <CardContent className="space-y-3 pt-5">
                {t.blocked ? <Alert tone="warning" title="Tipping-off guardrail"><ShieldAlert className="hidden" />This request was blocked.</Alert> : null}
                {t.content ? <AnswerText text={t.content} /> : <Spinner />}
                {t.citations.length ? (
                  <ul className="grid gap-2">{t.citations.map((c) => <Citation key={c.ref} citation={c} />)}</ul>
                ) : null}
                {t.messageId ? <FeedbackButtons messageId={t.messageId} /> : null}
              </CardContent>
            </Card>
          ),
        )}
        {error ? <Alert tone="danger">{error}</Alert> : null}
      </div>
      <div className="flex items-end gap-2">
        <Textarea
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              submit();
            }
          }}
          placeholder="Ask a question about your AML/CTF obligations…"
          className="min-h-12"
          maxLength={4000}
        />
        <Button onClick={submit} loading={busy} aria-label="Send"><Send className="h-4 w-4" /></Button>
        {turns.length ? <Button variant="ghost" onClick={reset}>New</Button> : null}
      </div>
      <p className="text-xs text-slate-400">General information, not legal advice. Never use this chat to discuss a suspicious matter with a client.</p>
    </div>
  );
}
