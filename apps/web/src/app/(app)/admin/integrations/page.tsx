"use client";
import { useEffect, useState } from "react";
import { Badge, Button, Card, CardContent, CardHeader, CardTitle, Field, Input } from "@complymate/ui";
import { useSettings } from "../_settings";

export default function IntegrationsPage() {
  const { settings, save } = useSettings();
  const [domain, setDomain] = useState("");
  useEffect(() => { if (settings?.integrations?.email_domain) setDomain(String(settings.integrations.email_domain)); }, [settings]);
  return (
    <div className="grid gap-4 md:grid-cols-2">
      <Card>
        <CardHeader><CardTitle>Email domain</CardTitle></CardHeader>
        <CardContent className="space-y-3">
          <Field label="Your firm's email domain" hint="Used to suggest invitations and to flag external addresses."><Input value={domain} onChange={(e) => setDomain(e.target.value)} placeholder="yourfirm.com.au" /></Field>
          <Button loading={save.isPending} onClick={() => save.mutate({ integrations: { ...(settings?.integrations ?? {}), email_domain: domain } })}>Save</Button>
        </CardContent>
      </Card>
      {[["Xero", "Sync clients from your practice ledger."], ["Practice management", "Connect your practice management system."], ["Electronic verification", "Verify identity electronically (provider integration)."], ["PEP screening provider", "Automated PEP and adverse media checks."]].map(([name, desc]) => (
        <Card key={name}>
          <CardHeader className="flex-row items-center justify-between"><CardTitle>{name}</CardTitle><Badge>Coming soon</Badge></CardHeader>
          <CardContent className="text-sm text-slate-500">{desc}</CardContent>
        </Card>
      ))}
    </div>
  );
}
