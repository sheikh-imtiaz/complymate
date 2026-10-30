"use client";
import type { ReactNode } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect } from "react";
import { useQuery } from "@tanstack/react-query";
import { Activity, Bot, BookOpen, Building2, DollarSign, Flag, GraduationCap, LogOut, ScrollText, ShieldQuestion, UserCog } from "lucide-react";
import { Badge, Button, cn, Spinner } from "@complymate/ui";
import { get } from "@/lib/api-client";
import { signOut } from "@/lib/auth";
import { StepUpNotice } from "./StepUpNotice";

interface Me { email: string; platform_role: string | null; permissions: string[] }

const NAV = [
  ["/tenants", "Tenants", Building2, "platform:tenants:read"],
  ["/feature-flags", "Feature flags", Flag, "platform:tenants:read"],
  ["/knowledge-base", "Rule library", BookOpen, "platform:content:update"],
  ["/templates", "Training templates", GraduationCap, "platform:content:update"],
  ["/quizzes", "Quiz review", ShieldQuestion, "platform:content:update"],
  ["/ai-quality", "AI quality", Bot, "platform:ai_quality"],
  ["/usage-costs", "Usage & LLM cost", DollarSign, "platform:usage:read"],
  ["/impersonation", "Support access", UserCog, "platform:impersonate"],
  ["/system-health", "System health", Activity, "platform:health:read"],
  ["/audit-log", "Platform audit log", ScrollText, "platform:audit:read"],
] as const;

export function AdminShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const { data: me, error, isLoading } = useQuery({ queryKey: ["me"], queryFn: () => get<Me>("/auth/me"), retry: false });
  useEffect(() => {
    if (error) router.replace("/sign-in");
  }, [error, router]);
  if (pathname.startsWith("/sign-in") || pathname.startsWith("/callback")) return <>{children}</>;
  if (isLoading || !me) return <div className="flex min-h-screen items-center justify-center"><Spinner /></div>;
  if (!me.platform_role) {
    return <div className="p-10 text-center">This console is for ComplyMate staff only. <Button variant="link" onClick={() => void signOut()}>Sign out</Button></div>;
  }
  return (
    <div className="flex min-h-screen">
      <aside className="w-60 shrink-0 bg-slate-900 text-slate-200">
        <div className="px-5 py-4 text-lg font-semibold text-white">ComplyMate <span className="text-xs font-normal text-slate-400">platform</span></div>
        <nav className="space-y-0.5 px-3">
          {NAV.filter(([, , , p]) => me.permissions.includes(p)).map(([href, label, Icon]) => (
            <Link key={href} href={href} className={cn("flex items-center gap-3 rounded-md px-3 py-2 text-sm hover:bg-slate-800", pathname.startsWith(href) && "bg-slate-800 text-white")}>
              <Icon className="h-4 w-4" />{label}
            </Link>
          ))}
        </nav>
      </aside>
      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex h-14 items-center justify-between border-b border-slate-200 bg-white px-6">
          <Badge tone="warning">{me.platform_role.replace(/_/g, " ")}</Badge>
          <div className="flex items-center gap-3 text-sm text-slate-600">{me.email}<Button variant="ghost" size="icon" onClick={() => void signOut()} aria-label="Sign out"><LogOut className="h-4 w-4" /></Button></div>
        </header>
        <main className="mx-auto w-full max-w-7xl flex-1 p-6">{children}</main>
      </div>
      <StepUpNotice />
    </div>
  );
}
