import { Badge } from "@complymate/ui";

export interface CompareSection { key: string; title: string; changed: boolean; diff: string[] }

export function VersionDiff({ sections }: { sections: CompareSection[] }) {
  return (
    <div className="space-y-4">
      {sections.map((s) => (
        <div key={s.key} className="rounded-lg border border-slate-200 bg-white p-4">
          <div className="mb-2 flex items-center gap-2">
            <h3 className="font-semibold">{s.title}</h3>
            <Badge tone={s.changed ? "warning" : "neutral"}>{s.changed ? "Changed" : "No change"}</Badge>
          </div>
          {s.changed ? (
            <pre className="overflow-x-auto whitespace-pre-wrap text-xs leading-relaxed">
              {s.diff.map((line, i) => (
                <div key={i} className={line.startsWith("+ ") ? "bg-green-50 text-green-800" : line.startsWith("- ") ? "bg-red-50 text-red-800 line-through" : "text-slate-600"}>
                  {line}
                </div>
              ))}
            </pre>
          ) : null}
        </div>
      ))}
    </div>
  );
}
