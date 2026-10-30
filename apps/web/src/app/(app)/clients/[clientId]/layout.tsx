"use client";
import { use, type ReactNode } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import type { Client } from "@complymate/api-types";
import { cn, PageHeader, Spinner } from "@complymate/ui";
import { RiskBadge, StatusBadge } from "@/components/clients/RiskBadge";
import { ShareDialog } from "@/components/collaboration/ShareDialog";
import { get } from "@/lib/api-client";
import { usePermissions } from "@/hooks/usePermission";

const TABS = [
  ["", "Overview"], ["/owners", "Owners"], ["/documents", "Documents"], ["/screening", "Screening"], ["/risk", "Risk"], ["/activity", "Activity"],
] as const;

export default function ClientLayout({ children, params }: { children: ReactNode; params: Promise<{ clientId: string }> }) {
  const { clientId } = use(params);
  const pathname = usePathname();
  const can = usePermissions();
  const { data } = useQuery({ queryKey: ["client", clientId], queryFn: () => get<Client>(`/clients/${clientId}`) });
  if (!data) return <Spinner />;
  const base = `/clients/${clientId}`;
  return (
    <>
      <PageHeader
        title={data.display_name}
        description={`${data.client_type} client`}
        actions={<div className="flex items-center gap-2"><StatusBadge status={data.status} /><RiskBadge level={data.risk_level} />{can("share:create") ? <ShareDialog resourceType="client" resourceId={clientId} /> : null}</div>}
      />
      <nav className="mb-6 flex gap-1 border-b border-slate-200">
        {TABS.map(([suffix, label]) => (
          <Link key={label} href={`${base}${suffix}`} className={cn("border-b-2 px-3 py-2 text-sm", pathname === `${base}${suffix}` ? "border-brand-600 font-medium text-brand-700" : "border-transparent text-slate-500 hover:text-slate-800")}>
            {label}
          </Link>
        ))}
      </nav>
      {children}
    </>
  );
}
