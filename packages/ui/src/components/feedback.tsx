import * as React from "react";
import { AlertTriangle, Info, CheckCircle2, XCircle } from "lucide-react";
import { cn } from "../lib";

const tones = {
  info: { cls: "border-brand-100 bg-brand-50 text-brand-700", Icon: Info },
  warning: { cls: "border-amber-200 bg-amber-50 text-amber-800", Icon: AlertTriangle },
  success: { cls: "border-green-200 bg-green-50 text-green-800", Icon: CheckCircle2 },
  danger: { cls: "border-red-200 bg-red-50 text-red-800", Icon: XCircle },
};

export function Alert({ tone = "info", title, children, className }:
  { tone?: keyof typeof tones; title?: string; children?: React.ReactNode; className?: string }) {
  const { cls, Icon } = tones[tone];
  return (
    <div role="alert" className={cn("flex gap-3 rounded-lg border p-3 text-sm", cls, className)}>
      <Icon className="mt-0.5 h-4 w-4 shrink-0" />
      <div>
        {title ? <p className="font-semibold">{title}</p> : null}
        {children ? <div className="mt-0.5">{children}</div> : null}
      </div>
    </div>
  );
}

export function Spinner({ className }: { className?: string }) {
  return <span className={cn("inline-block h-5 w-5 animate-spin rounded-full border-2 border-brand-600 border-t-transparent", className)} aria-label="Loading" />;
}

export function EmptyState({ title, description, action }: { title: string; description?: string; action?: React.ReactNode }) {
  return (
    <div className="flex flex-col items-center justify-center gap-2 rounded-xl border border-dashed border-slate-300 p-10 text-center">
      <p className="font-medium text-slate-800">{title}</p>
      {description ? <p className="max-w-md text-sm text-slate-500">{description}</p> : null}
      {action}
    </div>
  );
}

export function PageHeader({ title, description, actions }: { title: string; description?: string; actions?: React.ReactNode }) {
  return (
    <div className="mb-6 flex flex-wrap items-start justify-between gap-4">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight text-slate-900">{title}</h1>
        {description ? <p className="mt-1 text-sm text-slate-500">{description}</p> : null}
      </div>
      {actions ? <div className="flex gap-2">{actions}</div> : null}
    </div>
  );
}

export function Stat({ label, value, hint, tone }: { label: string; value: React.ReactNode; hint?: string; tone?: "danger" | "warning" | "success" }) {
  const color = tone === "danger" ? "text-risk-high" : tone === "warning" ? "text-risk-medium" : tone === "success" ? "text-risk-low" : "text-slate-900";
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <p className="text-xs font-medium uppercase tracking-wide text-slate-500">{label}</p>
      <p className={cn("mt-1 text-2xl font-semibold", color)}>{value}</p>
      {hint ? <p className="mt-1 text-xs text-slate-500">{hint}</p> : null}
    </div>
  );
}
