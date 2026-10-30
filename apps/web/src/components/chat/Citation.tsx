import { ExternalLink } from "lucide-react";
import type { Citation as C } from "@/lib/ws";
import { formatDate } from "@/lib/format";

export function Citation({ citation }: { citation: C }) {
  return (
    <li className="flex items-start gap-2 rounded-md border border-slate-200 bg-slate-50 p-2 text-xs">
      <span className="rounded bg-brand-600 px-1.5 py-0.5 font-semibold text-white">{citation.ref}</span>
      <div className="min-w-0">
        <p className="font-medium text-slate-800">
          {citation.title}
          {citation.heading ? <span className="font-normal text-slate-500"> — {citation.heading}</span> : null}
        </p>
        <p className="text-slate-500">
          {citation.publisher} · last checked {formatDate(citation.last_checked_at)}
          {citation.url ? (
            <a href={citation.url} target="_blank" rel="noreferrer" className="ml-2 inline-flex items-center gap-1 text-brand-600 hover:underline">
              source <ExternalLink className="h-3 w-3" />
            </a>
          ) : null}
        </p>
      </div>
    </li>
  );
}
