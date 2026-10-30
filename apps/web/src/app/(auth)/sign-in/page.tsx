"use client";
import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Alert, Button, Card, CardContent, CardHeader, CardTitle, Field, Input } from "@complymate/ui";
import { authMode, signIn } from "@/lib/auth";
import { post } from "@/lib/api-client";

const DEMO = ["owner@demo.test", "amlco@demo.test", "manager@demo.test", "staff@demo.test", "auditor@demo.test"];

export default function SignInPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function go(address?: string) {
    setBusy(true);
    setError(null);
    try {
      await signIn(address ?? email);
      if (authMode === "dev") {
        await post("/auth/session");
        router.push("/dashboard");
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Sign-in failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Card>
      <CardHeader><CardTitle>Sign in</CardTitle></CardHeader>
      <CardContent className="space-y-4">
        {authMode === "oidc" ? (
          <Button className="w-full" loading={busy} onClick={() => void go()}>Continue to secure sign-in</Button>
        ) : (
          <>
            <Alert tone="info" title="Local development">No password needed. Sign in as a seeded user.</Alert>
            <Field label="Email"><Input type="email" value={email} onChange={(e) => setEmail(e.target.value)} /></Field>
            <Button className="w-full" loading={busy} onClick={() => void go()} disabled={!email}>Sign in</Button>
            <div className="flex flex-wrap gap-2">
              {DEMO.map((d) => <button key={d} className="text-xs text-brand-600 hover:underline" onClick={() => void go(d)}>{d}</button>)}
            </div>
          </>
        )}
        {error ? <Alert tone="danger">{error}</Alert> : null}
        <p className="text-sm text-slate-500">New firm? <Link href="/sign-up" className="text-brand-600 hover:underline">Create an account</Link></p>
      </CardContent>
    </Card>
  );
}
