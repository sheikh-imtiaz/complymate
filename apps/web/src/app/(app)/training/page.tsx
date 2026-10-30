"use client";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import type { TrainingModule } from "@complymate/api-types";
import { Badge, Card, CardContent, CardDescription, CardHeader, CardTitle, PageHeader, Table, TBody, TD, TH, THead, TR } from "@complymate/ui";
import { get } from "@/lib/api-client";
import { formatDate } from "@/lib/format";
import { usePermission } from "@/hooks/usePermission";

interface My { assignments: { module_id: string; due_date: string | null; completed_at: string | null; overdue: boolean }[]; attempts: { id: string; module_id: string; score: string; passed: boolean }[] }
interface StatusRow { user_id: string; full_name: string | null; role: string; assigned: number; completed: number; overdue: number }

export default function TrainingPage() {
  const { scope } = usePermission("training:read");
  const { data: modules = [] } = useQuery({ queryKey: ["modules"], queryFn: () => get<TrainingModule[]>("/training/modules") });
  const { data: my } = useQuery({ queryKey: ["my-training"], queryFn: () => get<My>("/training/my") });
  const { data: status } = useQuery({ queryKey: ["training-status"], queryFn: () => get<StatusRow[]>("/training/status"), enabled: scope === "all" });
  return (
    <>
      <PageHeader title="Training" description="Short modules per role, with quizzes and certificates." />
      <div className="grid gap-4 md:grid-cols-2">
        {modules.map((m) => {
          const a = my?.assignments.find((x) => x.module_id === m.id);
          const passed = my?.attempts.some((x) => x.module_id === m.id && x.passed);
          return (
            <Link key={m.id} href={`/training/${m.id}`}>
              <Card className="h-full hover:border-brand-300">
                <CardHeader>
                  <CardTitle>{m.title}</CardTitle>
                  <CardDescription>{m.description}</CardDescription>
                </CardHeader>
                <CardContent className="flex flex-wrap gap-2 text-xs">
                  <Badge>{m.duration_minutes} min</Badge>
                  {passed ? <Badge tone="success">Completed</Badge> : a?.overdue ? <Badge tone="danger">Overdue</Badge> : a ? <Badge tone="info">Due {formatDate(a.due_date)}</Badge> : null}
                </CardContent>
              </Card>
            </Link>
          );
        })}
      </div>
      {status ? (
        <Card className="mt-6">
          <CardHeader><CardTitle>Team completion</CardTitle></CardHeader>
          <CardContent>
            <Table>
              <THead><TR><TH>Person</TH><TH>Role</TH><TH>Assigned</TH><TH>Completed</TH><TH>Overdue</TH></TR></THead>
              <TBody>{status.map((s) => <TR key={s.user_id}><TD>{s.full_name}</TD><TD>{s.role}</TD><TD>{s.assigned}</TD><TD>{s.completed}</TD><TD className={s.overdue ? "text-risk-high" : ""}>{s.overdue}</TD></TR>)}</TBody>
            </Table>
          </CardContent>
        </Card>
      ) : null}
    </>
  );
}
