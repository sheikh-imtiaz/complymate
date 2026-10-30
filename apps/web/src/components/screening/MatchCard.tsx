import { Badge, Button, Card, CardContent } from "@complymate/ui";
import { formatDateTime } from "@/lib/format";

export interface ScreeningMatch {
  id: string;
  client_id: string;
  subject_name: string;
  matched_name: string;
  score: string | number;
  method: string;
  status: string;
  review_note: string | null;
  created_at: string;
  entry: { source: string; reference: string; primary_name: string; aliases: string[]; dob: string | null; nationality: string | null; program: string | null; entity_type: string };
}

export function MatchCard({ match, onReview }: { match: ScreeningMatch; onReview?: () => void }) {
  const score = Number(match.score);
  return (
    <Card>
      <CardContent className="flex flex-wrap items-start justify-between gap-4 pt-5">
        <div className="space-y-1 text-sm">
          <p className="font-semibold">{match.subject_name} <span className="font-normal text-slate-500">matched</span> {match.entry.primary_name}</p>
          <p className="text-slate-600">{match.entry.source} · ref {match.entry.reference} · {match.entry.program ?? "—"}</p>
          <p className="text-slate-500">DOB {match.entry.dob ?? "unknown"} · nationality {match.entry.nationality ?? "unknown"}</p>
          {match.entry.aliases.length ? <p className="text-slate-500">Aliases: {match.entry.aliases.join(", ")}</p> : null}
          <p className="text-xs text-slate-400">Found {formatDateTime(match.created_at)} · {match.method}</p>
        </div>
        <div className="flex flex-col items-end gap-2">
          <Badge tone={score >= 95 ? "danger" : "warning"}>Score {score}</Badge>
          <Badge>{match.status.replace(/_/g, " ")}</Badge>
          {onReview && (match.status === "open" || match.status === "needs_info") ? <Button size="sm" onClick={onReview}>Review</Button> : null}
        </div>
      </CardContent>
    </Card>
  );
}
