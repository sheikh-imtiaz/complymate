"use client";
import Link from "next/link";
import { LogOut, UserCircle } from "lucide-react";
import { Badge, Button, Select } from "@complymate/ui";
import { signOut } from "@/lib/auth";
import { useTenant } from "@/hooks/useTenant";
import { humanize } from "@/lib/format";
import { NotificationBell } from "./NotificationBell";

export function TopBar() {
  const { me, tenantId, switchTenant, role } = useTenant();
  return (
    <header className="flex h-14 items-center justify-between gap-4 border-b border-slate-200 bg-white px-4">
      <div className="flex items-center gap-3">
        {me && me.memberships.length > 1 ? (
          <Select value={tenantId ?? ""} onChange={(e) => switchTenant(e.target.value)} className="w-64" aria-label="Firm">
            {me.memberships.map((m) => (
              <option key={m.tenant_id} value={m.tenant_id}>{m.tenant_name}</option>
            ))}
          </Select>
        ) : (
          <span className="font-medium text-slate-800">{me?.memberships[0]?.tenant_name}</span>
        )}
        {role ? <Badge tone="info">{humanize(role)}</Badge> : null}
        {me?.impersonation_id ? <Badge tone="warning">Support session (read-only)</Badge> : null}
      </div>
      <div className="flex items-center gap-1">
        <NotificationBell />
        <Button asChild variant="ghost" size="icon" aria-label="Profile">
          <Link href="/profile"><UserCircle className="h-5 w-5" /></Link>
        </Button>
        <Button variant="ghost" size="icon" aria-label="Sign out" onClick={() => void signOut()}>
          <LogOut className="h-4 w-4" />
        </Button>
      </div>
    </header>
  );
}
