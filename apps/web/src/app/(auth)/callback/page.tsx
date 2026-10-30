"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Alert, Spinner } from "@complymate/ui";
import { completeSignIn } from "@/lib/auth";
import { get, post } from "@/lib/api-client";

interface MeLite { tenant_id: string | null; memberships: { tenant_id: string }[] }

export default function CallbackPage() {
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    (async () => {
      try {
        await completeSignIn();
        await post("/auth/session");
        const returnTo = sessionStorage.getItem("cm_return_to");
        sessionStorage.removeItem("cm_return_to");
        const invite = sessionStorage.getItem("cm_invite_token");
        if (invite) return router.replace(`/accept-invite?token=${encodeURIComponent(invite)}`);
        const me = await get<MeLite>("/auth/me");
        router.replace(returnTo ?? (me.memberships.length ? "/dashboard" : "/onboarding"));
      } catch (e) {
        setError(e instanceof Error ? e.message : "Sign-in could not be completed");
      }
    })();
  }, [router]);
  return error ? <Alert tone="danger" title="Sign-in failed">{error}</Alert> : <div className="flex justify-center"><Spinner /></div>;
}
