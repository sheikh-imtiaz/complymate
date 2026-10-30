"use client";
import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Card, CardContent, CardHeader, CardTitle, EmptyState, PageHeader, Select, Spinner, Table, TBody, TD, TH, THead, TR } from "@complymate/ui";
import { MatchCard, type ScreeningMatch } from "@/components/screening/MatchCard";
import { MatchReviewDialog } from "@/components/screening/MatchReviewDialog";
import { get } from "@/lib/api-client";
import { formatDateTime } from "@/lib/format";
import { usePermissions } from "@/hooks/usePermission";

interface WatchlistVersion { id: string; source: string; version_label: string; entry_count: number; fetched_at: string }

export default function ScreeningQueuePage() {
  const qc = useQueryClient();
  const can = usePermissions();
  const [status, setStatus] = useState("open");
  const { data, isLoading } = useQuery({ queryKey: ["matches", status], queryFn: () => get<ScreeningMatch[]>(`/screening/matches?status=${status}`) });
  const { data: lists = [] } = useQuery({ queryKey: ["watchlists"], queryFn: () => get<WatchlistVersion[]>("/screening/watchlists") });
  const [review, setReview] = useState<ScreeningMatch | null>(null);
  return (
    <>
      <PageHeader title="Screening review queue" description="Possible sanctions matches from onboarding and nightly re-screening." />
      <div className="grid gap-6 lg:grid-cols-[1fr_320px]">
        <div className="space-y-3">
          <Select value={status} onChange={(e) => setStatus(e.target.value)} className="w-56" aria-label="Status">
            <option value="open">Open</option><option value="needs_info">Needs info</option><option value="true_match">True match</option><option value="false_positive">False positive</option>
          </Select>
          {isLoading ? <Spinner /> : !data?.length ? <EmptyState title="Nothing to review" description="New possible matches will appear here." /> : null}
          {data?.map((m) => <MatchCard key={m.id} match={m} onReview={can("screening:update") ? () => setReview(m) : undefined} />)}
        </div>
        <Card className="h-fit">
          <CardHeader><CardTitle>Lists in use</CardTitle></CardHeader>
          <CardContent>
            <Table>
              <THead><TR><TH>Source</TH><TH>Entries</TH><TH>Updated</TH></TR></THead>
              <TBody>{lists.map((l) => <TR key={l.id}><TD>{l.source}</TD><TD>{l.entry_count}</TD><TD>{formatDateTime(l.fetched_at)}</TD></TR>)}</TBody>
            </Table>
          </CardContent>
        </Card>
      </div>
      <MatchReviewDialog match={review} onClose={() => setReview(null)} onDone={() => { setReview(null); void qc.invalidateQueries({ queryKey: ["matches"] }); }} />
    </>
  );
}
