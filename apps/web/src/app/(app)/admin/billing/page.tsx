"use client";
import { useQuery } from "@tanstack/react-query";
import type { Billing } from "@complymate/api-types";
import { Alert, Badge, Button, Card, CardContent, CardHeader, CardTitle, Spinner } from "@complymate/ui";
import { get, post } from "@/lib/api-client";
import { formatDate, formatMoney, humanize } from "@/lib/format";
import { usePermissions } from "@/hooks/usePermission";

export default function BillingPage() {
  const can = usePermissions();
  const { data } = useQuery({ queryKey: ["billing"], queryFn: () => get<Billing>("/billing") });
  if (!data) return <Spinner />;
  const go = async (path: string, body?: unknown) => {
    const { url } = await post<{ url: string }>(path, body);
    window.location.href = url;
  };
  return (
    <div className="space-y-6">
      <Card>
        <CardHeader className="flex-row items-center justify-between">
          <CardTitle>{data.plan_name} plan — {formatMoney(data.price_cents)}/month</CardTitle>
          <Badge tone={data.status === "active" ? "success" : "warning"}>{humanize(data.status)}</Badge>
        </CardHeader>
        <CardContent className="space-y-3 text-sm">
          {data.trial_ends_at && data.status === "trialing" ? <Alert tone="info">Trial ends {formatDate(data.trial_ends_at)}.</Alert> : null}
          <p>Seats: {data.seats} of {data.max_users}</p>
          {data.current_period_end ? <p>Renews {formatDate(data.current_period_end)}</p> : null}
          {can("billing:update") ? (
            <div className="flex flex-wrap gap-2">
              <Button onClick={() => void go("/billing/checkout", { plan_code: "solo", include_onboarding: !data.onboarding_paid })}>Choose Solo (A$79)</Button>
              <Button onClick={() => void go("/billing/checkout", { plan_code: "practice", include_onboarding: !data.onboarding_paid })}>Choose Practice (A$249)</Button>
              <Button variant="secondary" onClick={() => void go("/billing/portal")}>Invoices &amp; payment method</Button>
            </div>
          ) : null}
        </CardContent>
      </Card>
      <Card>
        <CardHeader><CardTitle>Usage this month</CardTitle></CardHeader>
        <CardContent className="space-y-3">
          {data.limits.map((l) => (
            <div key={l.metric}>
              <div className="flex justify-between text-sm"><span>{humanize(l.metric)}</span><span>{l.used} / {l.limit}</span></div>
              <div className="mt-1 h-2 overflow-hidden rounded bg-slate-100">
                <div className={`h-full ${l.blocked ? "bg-red-600" : l.warning ? "bg-amber-500" : "bg-brand-600"}`} style={{ width: `${Math.min(100, (l.used / Math.max(1, l.limit)) * 100)}%` }} />
              </div>
              {l.message ? <p className="mt-1 text-xs text-amber-700">{l.message}</p> : null}
            </div>
          ))}
        </CardContent>
      </Card>
    </div>
  );
}
