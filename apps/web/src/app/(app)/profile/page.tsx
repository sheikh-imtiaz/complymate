"use client";
import { Badge, Button, Card, CardContent, CardHeader, CardTitle, PageHeader } from "@complymate/ui";
import { signOut, stepUp } from "@/lib/auth";
import { formatDateTime, humanize } from "@/lib/format";
import { useTenant } from "@/hooks/useTenant";

export default function ProfilePage() {
  const { me } = useTenant();
  if (!me) return null;
  return (
    <>
      <PageHeader title="Your profile" />
      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader><CardTitle>Account</CardTitle></CardHeader>
          <CardContent className="space-y-2 text-sm">
            <p><span className="text-slate-500">Name:</span> {me.full_name ?? "—"}</p>
            <p><span className="text-slate-500">Email:</span> {me.email}</p>
            <p><span className="text-slate-500">Role:</span> {humanize(me.role_key)}</p>
            <p><span className="text-slate-500">Firms:</span> {me.memberships.map((m) => m.tenant_name).join(", ")}</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader><CardTitle>Security</CardTitle></CardHeader>
          <CardContent className="space-y-3 text-sm">
            <p>MFA: {me.mfa_verified ? <Badge tone="success">Verified this session</Badge> : <Badge tone="warning">Not verified</Badge>}</p>
            <p><span className="text-slate-500">Signed in:</span> {formatDateTime(me.auth_time)}</p>
            <p><span className="text-slate-500">Sensitive actions allowed until:</span> {formatDateTime(me.step_up_valid_until)}</p>
            <p className="text-slate-500">MFA devices and passkeys are managed on the secure sign-in page. Ask your firm owner to reset MFA if you lose your device.</p>
            <div className="flex gap-2">
              <Button variant="secondary" onClick={() => void stepUp()}>Re-verify now</Button>
              <Button variant="destructive" onClick={() => void signOut()}>Sign out</Button>
            </div>
          </CardContent>
        </Card>
      </div>
    </>
  );
}
