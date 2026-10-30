import Link from "next/link";
import { Card, CardContent, CardHeader, CardTitle } from "@complymate/ui";

export default function MfaPage() {
  return (
    <Card>
      <CardHeader><CardTitle>Multi-factor authentication</CardTitle></CardHeader>
      <CardContent className="space-y-3 text-sm text-slate-600">
        <p>ComplyMate requires MFA for every user. You set it up during your first sign-in with an authenticator app (TOTP). Passkeys can be enabled by your firm.</p>
        <p>Lost your device? Ask your firm owner to reset your MFA from Firm admin → Users. You will enrol again at your next sign-in.</p>
        <Link href="/sign-in" className="text-brand-600 hover:underline">Back to sign in</Link>
      </CardContent>
    </Card>
  );
}
