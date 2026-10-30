"use client";
import type { ReactNode } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn, PageHeader } from "@complymate/ui";
import { usePermissions } from "@/hooks/usePermission";

const LINKS = [
  ["/admin/users", "Users", "user:read"], ["/admin/roles", "Roles", "user:read"], ["/admin/security", "Security", "settings:read"],
  ["/admin/retention", "Data retention", "settings:read"], ["/admin/branding", "Branding", "settings:read"],
  ["/admin/integrations", "Integrations", "settings:read"], ["/admin/api-keys", "API keys", "settings:read"], ["/admin/billing", "Billing", "billing:read"],
] as const;

export default function AdminLayout({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const can = usePermissions();
  return (
    <>
      <PageHeader title="Firm admin" description="Users, security, retention, branding, integrations and billing." />
      <nav className="mb-6 flex flex-wrap gap-1 border-b border-slate-200">
        {LINKS.filter(([, , p]) => can(p)).map(([href, label]) => (
          <Link key={href} href={href} className={cn("border-b-2 px-3 py-2 text-sm", pathname === href ? "border-brand-600 font-medium text-brand-700" : "border-transparent text-slate-500 hover:text-slate-800")}>{label}</Link>
        ))}
      </nav>
      {children}
    </>
  );
}
