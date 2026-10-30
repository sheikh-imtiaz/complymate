"use client";
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Alert, Button, Card, CardContent, CardHeader, CardTitle, Field, Input, Select } from "@complymate/ui";
import { get, post } from "@/lib/api-client";
import { setTenantId } from "@/lib/auth";

interface Question { code: string; question: string; designated: boolean }
interface Applicability { applies: boolean; explanation: string; designated_services: string[] }

/** Firm setup: profile, designated services check (does Tranche 2 apply?), plan. Then AMLCO + invites in admin. */
export default function OnboardingPage() {
  const { data: questions = [] } = useQuery({ queryKey: ["designated"], queryFn: () => get<Question[]>("/tenants/designated-services") });
  const [step, setStep] = useState(1);
  const [form, setForm] = useState({ name: "", jurisdiction: "AU", entity_type: "company", abn: "", nzbn: "", size: "2-10", plan_code: "solo" });
  const [services, setServices] = useState<string[]>([]);
  const [result, setResult] = useState<Applicability | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function check() {
    setResult(await post<Applicability>("/tenants/check-applicability", { jurisdiction: form.jurisdiction, services }));
    setStep(3);
  }
  async function create() {
    setBusy(true);
    setError(null);
    try {
      const tenant = await post<{ id: string }>("/tenants", {
        ...form, abn: form.abn || undefined, nzbn: form.nzbn || undefined, services,
      });
      setTenantId(tenant.id);
      window.location.href = "/admin/users?welcome=1";
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not create firm");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold">Set up your firm</h1>
      {step === 1 ? (
        <Card>
          <CardHeader><CardTitle>1. Firm profile</CardTitle></CardHeader>
          <CardContent className="grid gap-4 md:grid-cols-2">
            <Field label="Firm name"><Input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} /></Field>
            <Field label="Country">
              <Select value={form.jurisdiction} onChange={(e) => setForm({ ...form, jurisdiction: e.target.value })}>
                <option value="AU">Australia (AUSTRAC)</option>
                <option value="NZ">New Zealand (DIA)</option>
              </Select>
            </Field>
            <Field label="Entity type">
              <Select value={form.entity_type} onChange={(e) => setForm({ ...form, entity_type: e.target.value })}>
                {["sole_trader", "partnership", "company", "trust", "incorporated_legal_practice"].map((t) => <option key={t} value={t}>{t.replace(/_/g, " ")}</option>)}
              </Select>
            </Field>
            {form.jurisdiction === "AU" ? (
              <Field label="ABN" hint="11 digits"><Input value={form.abn} onChange={(e) => setForm({ ...form, abn: e.target.value })} /></Field>
            ) : (
              <Field label="NZBN"><Input value={form.nzbn} onChange={(e) => setForm({ ...form, nzbn: e.target.value })} /></Field>
            )}
            <Field label="Size">
              <Select value={form.size} onChange={(e) => setForm({ ...form, size: e.target.value })}>
                {["1", "2-10", "11-50", "51+"].map((s) => <option key={s}>{s}</option>)}
              </Select>
            </Field>
            <div className="md:col-span-2 flex justify-end"><Button disabled={form.name.length < 2} onClick={() => setStep(2)}>Next</Button></div>
          </CardContent>
        </Card>
      ) : null}
      {step === 2 ? (
        <Card>
          <CardHeader><CardTitle>2. Which services do you provide?</CardTitle></CardHeader>
          <CardContent className="space-y-3">
            {questions.map((q) => (
              <label key={q.code} className="flex items-start gap-3 text-sm">
                <input type="checkbox" className="mt-1" checked={services.includes(q.code)}
                  onChange={(e) => setServices(e.target.checked ? [...services, q.code] : services.filter((s) => s !== q.code))} />
                {q.question}
              </label>
            ))}
            <div className="flex justify-between"><Button variant="secondary" onClick={() => setStep(1)}>Back</Button><Button onClick={() => void check()}>Check obligations</Button></div>
          </CardContent>
        </Card>
      ) : null}
      {step === 3 && result ? (
        <Card>
          <CardHeader><CardTitle>3. Your obligations and plan</CardTitle></CardHeader>
          <CardContent className="space-y-4">
            <Alert tone={result.applies ? "warning" : "success"} title={result.applies ? "AML/CTF obligations likely apply" : "Obligations may not apply"}>{result.explanation}</Alert>
            <Field label="Plan">
              <Select value={form.plan_code} onChange={(e) => setForm({ ...form, plan_code: e.target.value })}>
                <option value="solo">Solo — A$79/month (up to 2 users)</option>
                <option value="practice">Practice — A$249/month (up to 10 users, custom roles, scheduled reports)</option>
              </Select>
            </Field>
            <p className="text-sm text-slate-500">Your 14-day trial starts now. Onboarding support (A$299) is optional at checkout.</p>
            {error ? <Alert tone="danger">{error}</Alert> : null}
            <div className="flex justify-between"><Button variant="secondary" onClick={() => setStep(2)}>Back</Button><Button loading={busy} onClick={() => void create()}>Create firm</Button></div>
          </CardContent>
        </Card>
      ) : null}
    </div>
  );
}
