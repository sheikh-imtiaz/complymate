"use client";
import { useEffect, type ReactNode } from "react";
import { usePathname, useRouter } from "next/navigation";
import { Spinner } from "@complymate/ui";
import { Sidebar } from "@/components/layout/Sidebar";
import { TopBar } from "@/components/layout/TopBar";
import { StepUpMfaDialog } from "@/components/auth/StepUpMfaDialog";
import { useTenant } from "@/hooks/useTenant";
import { setTenantId } from "@/lib/auth";

export default function AppLayout({ children }: { children: ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const { me, isLoading, error, tenantId } = useTenant();

  useEffect(() => {
    if (error) router.replace("/sign-in");
  }, [error, router]);
  useEffect(() => {
    if (!me) return;
    if (!me.tenant_id && me.memberships.length === 0 && pathname !== "/onboarding") router.replace("/onboarding");
    if (!me.tenant_id && me.memberships.length > 0 && !tenantId) setTenantId(me.memberships[0].tenant_id);
  }, [me, pathname, router, tenantId]);

  if (isLoading || !me) {
    return <div className="flex min-h-screen items-center justify-center"><Spinner /></div>;
  }
  if (pathname === "/onboarding") return <main className="mx-auto max-w-3xl p-6">{children}<StepUpMfaDialog /></main>;
  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <div className="flex min-w-0 flex-1 flex-col">
        <TopBar />
        <main className="mx-auto w-full max-w-7xl flex-1 p-6">{children}</main>
      </div>
      <StepUpMfaDialog />
    </div>
  );
}
