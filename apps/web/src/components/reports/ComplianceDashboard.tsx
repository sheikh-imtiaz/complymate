"use client";
import Link from "next/link";
import { Bar, BarChart, Cell, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Alert, Card, CardContent, CardHeader, CardTitle, Stat } from "@complymate/ui";

export interface Dashboard {
  clients_by_risk: Record<string, number>;
  clients_by_status: Record<string, number>;
  overdue_reviews: number;
  open_matches: number;
  open_tasks: number;
  overdue_tasks: number;
  training: { total: number; completed: number; overdue: number; completion_percent: number | null };
  program: { status: string | null; next_review: string | null };
  open_smrs: number | null;
  alerts: { level: string; text: string }[];
}

const RISK_COLORS: Record<string, string> = { low: "#1b7a3a", medium: "#b06b00", high: "#b42318", unassessed: "#94a3b8" };

export function ComplianceDashboard({ data }: { data: Dashboard }) {
  const risk = Object.entries(data.clients_by_risk).map(([name, value]) => ({ name, value }));
  const status = Object.entries(data.clients_by_status).map(([name, value]) => ({ name, value }));
  return (
    <div className="space-y-6">
      {data.alerts.map((a) => (
        <Alert key={a.text} tone={a.level === "critical" ? "danger" : a.level === "warning" ? "warning" : "info"}>{a.text}</Alert>
      ))}
      <div className="grid gap-4 md:grid-cols-4">
        <Stat label="Open screening matches" value={data.open_matches} tone={data.open_matches ? "warning" : undefined} />
        <Stat label="Overdue client reviews" value={data.overdue_reviews} tone={data.overdue_reviews ? "danger" : undefined} />
        <Stat label="Open tasks" value={data.open_tasks} hint={`${data.overdue_tasks} overdue`} />
        <Stat label="Training complete" value={data.training.completion_percent == null ? "—" : `${data.training.completion_percent}%`} hint={`${data.training.overdue} overdue`} />
      </div>
      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader><CardTitle>Clients by risk</CardTitle></CardHeader>
          <CardContent className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie data={risk} dataKey="value" nameKey="name" innerRadius={50} outerRadius={90} label>
                  {risk.map((r) => <Cell key={r.name} fill={RISK_COLORS[r.name] ?? "#64748b"} />)}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
        <Card>
          <CardHeader><CardTitle>Clients by status</CardTitle></CardHeader>
          <CardContent className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={status}>
                <XAxis dataKey="name" />
                <YAxis allowDecimals={false} />
                <Tooltip />
                <Bar dataKey="value" fill="#0f4c81" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      </div>
      <Card>
        <CardContent className="flex flex-wrap items-center justify-between gap-4 pt-5 text-sm">
          <p>AML/CTF program: <strong>{data.program.status ?? "not started"}</strong>{data.program.next_review ? ` · next review ${data.program.next_review}` : ""}</p>
          {data.open_smrs != null ? <p>Open suspicious matter cases: <strong>{data.open_smrs}</strong></p> : null}
          <Link href="/reports" className="text-brand-600 hover:underline">All reports →</Link>
        </CardContent>
      </Card>
    </div>
  );
}
