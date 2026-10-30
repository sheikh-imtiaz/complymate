import { Badge } from "@complymate/ui";

export function RiskBadge({ level }: { level?: string | null }) {
  if (!level) return <Badge>Not assessed</Badge>;
  const tone = level === "high" ? "danger" : level === "medium" ? "warning" : "success";
  return <Badge tone={tone}>{level[0].toUpperCase() + level.slice(1)} risk</Badge>;
}

export function StatusBadge({ status }: { status: string }) {
  const tone = status === "approved" ? "success" : status === "declined" ? "danger" : status === "exited" ? "neutral" : "info";
  return <Badge tone={tone}>{status[0].toUpperCase() + status.slice(1)}</Badge>;
}
