"use client";
import { Suspense, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Alert, Button, Card, CardContent, CardHeader, CardTitle, Field, Input } from "@complymate/ui";
import { authMode, getToken, signIn, setTenantId } from "@/lib/auth";
import { get, post } from "@/lib/api-client";

function AcceptInvite() {
  const params = useSearchParams();
  const router = useRouter();
  const token = params.get("token") ?? "";
  const [email, setEmail] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function accept() {
    setBusy(true);
    setError(null);
    try {
      if (!(await getToken())) {
        if (authMode === "oidc") {
          sessionStorage.setItem("cm_invite_token", token);
          await signIn();
          return;
        }
        await signIn(email);
      }
      await post("/invitations/accept", { token });
      sessionStorage.removeItem("cm_invite_token");
      const me = await get<{ memberships: { tenant_id: string }[] }>("/auth/me");
      if (me.memberships.length === 1) setTenantId(me.memberships[0].tenant_id);
      router.push("/dashboard");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not accept the invitation");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Card>
      <CardHeader><CardTitle>Join your firm on ComplyMate</CardTitle></CardHeader>
      <CardContent className="space-y-4">
        {authMode === "dev" ? <Field label="Your email (must match the invitation)"><Input value={email} onChange={(e) => setEmail(e.target.value)} /></Field> : null}
        <Button className="w-full" onClick={() => void accept()} loading={busy} disabled={!token}>Accept invitation</Button>
        {!token ? <Alert tone="warning">This link is missing its invitation token.</Alert> : null}
        {error ? <Alert tone="danger">{error}</Alert> : null}
      </CardContent>
    </Card>
  );
}

export default function AcceptInvitePage() {
  return <Suspense><AcceptInvite /></Suspense>;
}
