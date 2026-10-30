"use client";
import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Alert, Button, Card, CardContent, CardHeader, CardTitle, Field, Input } from "@complymate/ui";
import { authMode, signIn } from "@/lib/auth";

/** Step 1 of sign-up: create the identity (Cognito hosted UI verifies email and enrols MFA).
 * Step 2 (firm profile, designated services, AMLCO, plan) happens at /onboarding. */
export default function SignUpPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  async function start() {
    setBusy(true);
    try {
      await signIn(email);
      if (authMode === "dev") router.push("/onboarding");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not start sign-up");
    } finally {
      setBusy(false);
    }
  }
  return (
    <Card>
      <CardHeader><CardTitle>Create your firm&apos;s account</CardTitle></CardHeader>
      <CardContent className="space-y-4">
        <ol className="list-decimal space-y-1 pl-5 text-sm text-slate-600">
          <li>Verify your email and set up multi-factor authentication</li>
          <li>Tell us about your firm and services</li>
          <li>Check whether Tranche 2 applies, nominate your compliance officer and invite your team</li>
        </ol>
        {authMode === "dev" ? <Field label="Work email"><Input type="email" value={email} onChange={(e) => setEmail(e.target.value)} /></Field> : null}
        <Button className="w-full" loading={busy} onClick={() => void start()} disabled={authMode === "dev" && !email}>Get started — 14-day free trial</Button>
        {error ? <Alert tone="danger">{error}</Alert> : null}
        <p className="text-sm text-slate-500">Already have an account? <Link href="/sign-in" className="text-brand-600 hover:underline">Sign in</Link></p>
      </CardContent>
    </Card>
  );
}
