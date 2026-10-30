"use client";
import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useMutation, useQuery } from "@tanstack/react-query";
import type { SmrCase } from "@complymate/api-types";
import { Alert, Badge, Button, Card, CardContent, CardHeader, CardTitle, EmptyState, PageHeader, Table, TBody, TD, TH, THead, TR, Textarea } from "@complymate/ui";
import { get, post } from "@/lib/api-client";
import { formatDate, humanize } from "@/lib/format";

export default function SmrListPage() {
  const router = useRouter();
  const { data = [] } = useQuery({ queryKey: ["smr"], queryFn: () => get<SmrCase[]>("/smr") });
  const [summary, setSummary] = useState("");
  const raise = useMutation({
    mutationFn: () => post<SmrCase>("/smr", { summary }),
    onSuccess: (c) => router.push(`/smr/${c.id}`),
  });
  return (
    <>
      <PageHeader title="Suspicious matters" description="Raise an internal concern. Only the compliance officer, owner and senior managers can see cases." />
      <Alert tone="warning" title="Do not tip off" className="mb-6">Never tell the client, or anyone outside the compliance team, that a concern has been raised or a report may be made.</Alert>
      <div className="grid gap-6 lg:grid-cols-[1fr_360px]">
        <Card>
          <CardHeader><CardTitle>Cases</CardTitle></CardHeader>
          <CardContent>
            {!data.length ? <EmptyState title="No cases" /> : (
              <Table>
                <THead><TR><TH>Reference</TH><TH>Status</TH><TH>Raised</TH></TR></THead>
                <TBody>{data.map((c) => (
                  <TR key={c.id}><TD><Link className="text-brand-700 hover:underline" href={`/smr/${c.id}`}>{c.reference}</Link></TD><TD><Badge>{humanize(c.status)}</Badge></TD><TD>{formatDate(c.created_at)}</TD></TR>
                ))}</TBody>
              </Table>
            )}
          </CardContent>
        </Card>
        <Card className="h-fit">
          <CardHeader><CardTitle>Raise a concern</CardTitle></CardHeader>
          <CardContent className="space-y-3">
            <Textarea rows={6} value={summary} onChange={(e) => setSummary(e.target.value)} placeholder="What happened? Facts only: dates, amounts, what the client said or did." />
            <Button onClick={() => raise.mutate()} disabled={summary.trim().length < 10} loading={raise.isPending}>Save draft</Button>
          </CardContent>
        </Card>
      </div>
    </>
  );
}
