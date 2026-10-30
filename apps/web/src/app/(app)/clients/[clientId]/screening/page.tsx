"use client";
import { use, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import type { ScreeningRun } from "@complymate/api-types";
import { Button, Card, CardContent, CardHeader, CardTitle, Checkbox, Table, TBody, TD, TH, THead, TR, Textarea } from "@complymate/ui";
import { MatchCard, type ScreeningMatch } from "@/components/screening/MatchCard";
import { MatchReviewDialog } from "@/components/screening/MatchReviewDialog";
import { ReportExportButton } from "@/components/reports/ReportExportButton";
import { get, post } from "@/lib/api-client";
import { formatDateTime } from "@/lib/format";
import { usePermissions } from "@/hooks/usePermission";

export default function ClientScreeningPage({ params }: { params: Promise<{ clientId: string }> }) {
  const { clientId } = use(params);
  const qc = useQueryClient();
  const can = usePermissions();
  const key = ["client-screening", clientId];
  const { data } = useQuery({ queryKey: key, queryFn: () => get<{ runs: ScreeningRun[]; matches: ScreeningMatch[] }>(`/clients/${clientId}/screening`) });
  const [review, setReview] = useState<ScreeningMatch | null>(null);
  const [pep, setPep] = useState({ is_pep: false, details: "" });
  const refresh = () => { void qc.invalidateQueries({ queryKey: key }); void qc.invalidateQueries({ queryKey: ["client", clientId] }); };
  const run = useMutation({ mutationFn: () => post(`/clients/${clientId}/screen`), onSuccess: refresh });
  return (
    <div className="grid gap-6 lg:grid-cols-[1fr_320px]">
      <div className="space-y-4">
        <div className="flex gap-2">
          {can("screening:create") ? <Button onClick={() => run.mutate()} loading={run.isPending}>Run screening now</Button> : null}
          {data?.runs.length ? <ReportExportButton path={`/clients/${clientId}/screening/certificate`} filename="screening-certificate.pdf" label="Certificate" /> : null}
        </div>
        {data?.matches.map((m) => <MatchCard key={m.id} match={m} onReview={can("screening:update") ? () => setReview(m) : undefined} />)}
        <Card>
          <CardHeader><CardTitle>Screening history</CardTitle></CardHeader>
          <CardContent>
            <Table>
              <THead><TR><TH>When</TH><TH>Trigger</TH><TH>Names</TH><TH>Matches</TH></TR></THead>
              <TBody>{data?.runs.map((r) => <TR key={r.id}><TD>{formatDateTime(r.created_at)}</TD><TD>{r.trigger}</TD><TD>{r.screened_names.length}</TD><TD>{r.match_count}</TD></TR>)}</TBody>
            </Table>
          </CardContent>
        </Card>
      </div>
      <Card className="h-fit">
        <CardHeader><CardTitle>PEP declaration</CardTitle></CardHeader>
        <CardContent className="space-y-3">
          <p className="text-xs text-slate-500">PEP screening starts with the client&apos;s declaration. A provider check can be added later.</p>
          <Checkbox label="Client or a related party is a PEP" checked={pep.is_pep} onChange={(e) => setPep({ ...pep, is_pep: e.target.checked })} />
          <Textarea placeholder="Details (position, country, dates)" value={pep.details} onChange={(e) => setPep({ ...pep, details: e.target.value })} rows={3} />
          {can("client:update") ? <Button size="sm" onClick={async () => { await post(`/clients/${clientId}/pep-declaration`, pep); refresh(); }}>Save declaration</Button> : null}
        </CardContent>
      </Card>
      <MatchReviewDialog match={review} onClose={() => setReview(null)} onDone={() => { setReview(null); refresh(); }} />
    </div>
  );
}
