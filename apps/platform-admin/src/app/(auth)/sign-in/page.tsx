"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { Alert, Button, Card, CardContent, CardHeader, CardTitle, Field, Input } from "@complymate/ui";
import { authMode, signIn } from "@/lib/auth";

export default function SignIn() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [error, setError] = useState<string | null>(null);
  return (
    <main className="flex min-h-screen items-center justify-center bg-slate-900 p-6">
      <Card className="w-full max-w-sm">
        <CardHeader><CardTitle>ComplyMate platform console</CardTitle></CardHeader>
        <CardContent className="space-y-3">
          <p className="text-xs text-slate-500">Staff only. All access is logged in the platform audit log.</p>
          {authMode === "dev" ? <Field label="Email"><Input value={email} onChange={(e) => setEmail(e.target.value)} /></Field> : null}
          <Button className="w-full" onClick={async () => {
            try {
              await signIn(email);
              if (authMode === "dev") router.push("/tenants");
            } catch (e) {
              setError(e instanceof Error ? e.message : "Sign-in failed");
            }
          }}>Sign in</Button>
          {error ? <Alert tone="danger">{error}</Alert> : null}
        </CardContent>
      </Card>
    </main>
  );
}
