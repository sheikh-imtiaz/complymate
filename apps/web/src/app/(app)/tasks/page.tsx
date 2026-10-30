"use client";
import { useState } from "react";
import Link from "next/link";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import type { Task } from "@complymate/api-types";
import { Badge, Button, Card, CardContent, EmptyState, PageHeader, Select, Table, TBody, TD, TH, THead, TR } from "@complymate/ui";
import { get, patch } from "@/lib/api-client";
import { formatDate, humanize, isOverdue } from "@/lib/format";
import { useTenant } from "@/hooks/useTenant";

const LINKS: Record<string, (id: string) => string> = {
  client: (id) => `/clients/${id}`, program_version: (id) => `/program/${id}`, smr_case: (id) => `/smr/${id}`, program: () => "/program",
};

export default function TasksPage() {
  const qc = useQueryClient();
  const { role } = useTenant();
  const [scope, setScope] = useState("mine");
  const [status, setStatus] = useState("open");
  const { data = [] } = useQuery({ queryKey: ["tasks", scope, status], queryFn: () => get<Task[]>(`/tasks?scope=${scope}&status=${status}`) });
  const done = useMutation({ mutationFn: (id: string) => patch(`/tasks/${id}`, { status: "done" }), onSuccess: () => void qc.invalidateQueries({ queryKey: ["tasks"] }) });
  return (
    <>
      <PageHeader title="Tasks" description="Approvals, reviews, screening matches and reminders. Overdue tasks escalate to the compliance officer." />
      <Card>
        <CardContent className="space-y-4 pt-5">
          <div className="flex gap-3">
            {["owner", "amlco", "senior_manager"].includes(role ?? "") ? (
              <Select value={scope} onChange={(e) => setScope(e.target.value)} className="w-48" aria-label="Scope"><option value="mine">My tasks</option><option value="all">Everyone&apos;s tasks</option></Select>
            ) : null}
            <Select value={status} onChange={(e) => setStatus(e.target.value)} className="w-40" aria-label="Status"><option value="open">Open</option><option value="done">Done</option></Select>
          </div>
          {!data.length ? <EmptyState title="All clear" description="No tasks here." /> : (
            <Table>
              <THead><TR><TH>Task</TH><TH>Type</TH><TH>Due</TH><TH /></TR></THead>
              <TBody>
                {data.map((t) => (
                  <TR key={t.id}>
                    <TD>
                      {t.resource_type && LINKS[t.resource_type] ? <Link className="text-brand-700 hover:underline" href={LINKS[t.resource_type](t.resource_id ?? "")}>{t.title}</Link> : t.title}
                      {t.escalated_at ? <Badge tone="danger" className="ml-2">Escalated</Badge> : null}
                    </TD>
                    <TD>{humanize(t.type)}</TD>
                    <TD className={isOverdue(t.due_date) && t.status === "open" ? "text-risk-high" : ""}>{formatDate(t.due_date)}</TD>
                    <TD className="text-right">{t.status === "open" ? <Button size="sm" variant="secondary" onClick={() => done.mutate(t.id)}>Mark done</Button> : null}</TD>
                  </TR>
                ))}
              </TBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </>
  );
}
