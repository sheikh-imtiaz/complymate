"use client";
import type { AuditEvent } from "@complymate/api-types";
import { Dialog, DialogContent } from "@complymate/ui";
import { formatDateTime, humanize } from "@/lib/format";

const Json = ({ value }: { value: unknown }) => (
  <pre className="max-h-48 overflow-auto rounded bg-slate-900 p-3 text-xs text-slate-100">{JSON.stringify(value, null, 2)}</pre>
);

export function AuditDetailDrawer({ event, onClose }: { event: AuditEvent | null; onClose: () => void }) {
  if (!event) return null;
  return (
    <Dialog open onOpenChange={(o) => !o && onClose()}>
      <DialogContent title={`${humanize(event.action)} · ${humanize(event.resource_type)}`} description={formatDateTime(event.occurred_at)} className="max-w-2xl">
        <dl className="grid grid-cols-3 gap-2 text-sm">
          <dt className="text-slate-500">Actor</dt><dd className="col-span-2">{event.actor_id ?? "system"} ({humanize(event.actor_role)})</dd>
          <dt className="text-slate-500">Resource id</dt><dd className="col-span-2 break-all">{event.resource_id ?? "—"}</dd>
          <dt className="text-slate-500">Reason</dt><dd className="col-span-2">{event.reason ?? "—"}</dd>
          <dt className="text-slate-500">IP / request</dt><dd className="col-span-2">{event.ip ?? "—"} · {event.request_id ?? "—"}</dd>
          <dt className="text-slate-500">Hash chain</dt><dd className="col-span-2 break-all font-mono text-xs">prev {event.prev_hash ?? "genesis"}<br />this {event.hash}</dd>
        </dl>
        <div className="mt-4 grid gap-3">
          {event.before ? <div><p className="mb-1 text-xs font-semibold text-slate-500">Before</p><Json value={event.before} /></div> : null}
          {event.after ? <div><p className="mb-1 text-xs font-semibold text-slate-500">After</p><Json value={event.after} /></div> : null}
          {event.ai ? <div><p className="mb-1 text-xs font-semibold text-slate-500">AI details</p><Json value={event.ai} /></div> : null}
        </div>
      </DialogContent>
    </Dialog>
  );
}
