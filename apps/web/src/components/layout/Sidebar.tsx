"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useTranslations } from "next-intl";
import {
  BookOpenCheck, ClipboardList, FileText, GraduationCap, LayoutDashboard, MessageSquareText, ScrollText, Settings,
  ShieldAlert, ShieldCheck, Users, BarChart3,
} from "lucide-react";
import { cn } from "@complymate/ui";
import { usePermissions } from "@/hooks/usePermission";

const NAV = [
  { href: "/dashboard", key: "dashboard", icon: LayoutDashboard, perm: "report:read" },
  { href: "/program", key: "program", icon: BookOpenCheck, perm: "program:read" },
  { href: "/clients", key: "clients", icon: Users, perm: "client:read" },
  { href: "/screening", key: "screening", icon: ShieldCheck, perm: "screening:read" },
  { href: "/smr", key: "smr", icon: ShieldAlert, perm: "smr:create_draft" },
  { href: "/ask", key: "ask", icon: MessageSquareText, perm: "chat:use" },
  { href: "/training", key: "training", icon: GraduationCap, perm: "training:read" },
  { href: "/tasks", key: "tasks", icon: ClipboardList, perm: "task:read" },
  { href: "/reports", key: "reports", icon: BarChart3, perm: "report:read" },
  { href: "/audit-log", key: "auditLog", icon: ScrollText, perm: "audit:read" },
  { href: "/admin/users", key: "admin", icon: Settings, perm: "user:read" },
] as const;

export function Sidebar() {
  const t = useTranslations("nav");
  const pathname = usePathname();
  const can = usePermissions();
  return (
    <aside className="hidden w-60 shrink-0 border-r border-slate-200 bg-white md:flex md:flex-col">
      <Link href="/dashboard" className="flex items-center gap-2 px-5 py-4">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img src="/logo.svg" alt="" className="h-7 w-7" />
        <span className="text-lg font-semibold text-brand-700">ComplyMate</span>
      </Link>
      <nav className="flex-1 space-y-0.5 px-3 py-2">
        {NAV.filter((item) => can(item.perm)).map(({ href, key, icon: Icon }) => (
          <Link
            key={href}
            href={href}
            className={cn(
              "flex items-center gap-3 rounded-md px-3 py-2 text-sm text-slate-600 hover:bg-slate-100",
              pathname.startsWith(href.split("/").slice(0, 2).join("/")) && "bg-brand-50 font-medium text-brand-700",
            )}
          >
            <Icon className="h-4 w-4" />
            {t(key)}
          </Link>
        ))}
      </nav>
      <div className="flex items-center gap-2 border-t border-slate-100 px-5 py-3 text-xs text-slate-400">
        <FileText className="h-3.5 w-3.5" /> General information, not legal advice.
      </div>
    </aside>
  );
}
