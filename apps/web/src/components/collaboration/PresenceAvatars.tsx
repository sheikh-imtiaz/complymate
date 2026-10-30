"use client";
import { useQuery } from "@tanstack/react-query";
import { post } from "@/lib/api-client";

interface Presence { user_id: string; full_name: string | null; last_seen_at: string }

/** Heartbeat every 20 s; shows who else is viewing the program version. */
export function PresenceAvatars({ versionId }: { versionId: string }) {
  const { data = [] } = useQuery({
    queryKey: ["presence", versionId],
    queryFn: () => post<Presence[]>(`/program/versions/${versionId}/presence`),
    refetchInterval: 20_000,
  });
  return (
    <div className="flex -space-x-2" aria-label="People viewing">
      {data.map((p) => (
        <span key={p.user_id} title={p.full_name ?? "User"} className="flex h-7 w-7 items-center justify-center rounded-full border-2 border-white bg-brand-100 text-xs font-semibold text-brand-700">
          {(p.full_name ?? "?").split(" ").map((s) => s[0]).join("").slice(0, 2).toUpperCase()}
        </span>
      ))}
    </div>
  );
}
