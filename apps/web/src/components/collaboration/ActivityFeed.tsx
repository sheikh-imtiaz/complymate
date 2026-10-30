"use client";
import { useQuery } from "@tanstack/react-query";
import type { AuditEvent } from "@complymate/api-types";
import { get } from "@/lib/api-client";
import { formatDateTime, humanize } from "@/lib/format";

export function ActivityFeed({ clientId }: { clientId: string }) {
  const { data = [] } = useQuery({ queryKey: ["activity", clientId], queryFn: () => get<AuditEvent[]>(`/clients/${clientId}/activity`) });
  if (!data.length) return <p className="text-sm text-slate-500">No activity yet.</p>;
  return (
    <ol className="relative space-y-4 border-l border-slate-200 pl-5">
      {data.map((e) => (
        <li key={e.id} className="text-sm">
          <span className="absolute -left-1.5 mt-1.5 h-3 w-3 rounded-full border-2 border-white bg-brand-500" />
          <p className="font-medium">{humanize(e.action)} {humanize(e.resource_type).toLowerCase()}</p>
          <p className="text-xs text-slate-500">{formatDateTime(e.occurred_at)} · {humanize(e.actor_role)}{e.reason ? ` · ${e.reason}` : ""}</p>
        </li>
      ))}
    </ol>
  );
}
