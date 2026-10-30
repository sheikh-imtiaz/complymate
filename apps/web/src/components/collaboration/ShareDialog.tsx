"use client";
import { useState } from "react";
import { Share2 } from "lucide-react";
import { Button, Dialog, DialogContent, DialogTrigger, Field, Input } from "@complymate/ui";
import { post } from "@/lib/api-client";

export function ShareDialog({ resourceType, resourceId }: { resourceType: string; resourceId: string }) {
  const [open, setOpen] = useState(false);
  const [email, setEmail] = useState("");
  const [name, setName] = useState("");
  const [days, setDays] = useState(14);
  const [status, setStatus] = useState<string | null>(null);
  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild><Button variant="secondary" size="sm"><Share2 className="h-4 w-4" />Share</Button></DialogTrigger>
      <DialogContent title="Share with an external advisor" description="They can view this item only, until the share expires.">
        <div className="grid gap-3">
          <Field label="Advisor email"><Input type="email" value={email} onChange={(e) => setEmail(e.target.value)} /></Field>
          <Field label="Advisor name"><Input value={name} onChange={(e) => setName(e.target.value)} /></Field>
          <Field label="Expires in (days)" hint="Up to 90 days"><Input type="number" min={1} max={90} value={days} onChange={(e) => setDays(Number(e.target.value))} /></Field>
          {status ? <p className="text-sm text-slate-600">{status}</p> : null}
          <div className="flex justify-end">
            <Button
              disabled={!email}
              onClick={async () => {
                const expires = new Date(Date.now() + days * 86400_000).toISOString();
                try {
                  await post("/shares", { resource_type: resourceType, resource_id: resourceId, advisor_email: email, advisor_name: name || undefined, expires_at: expires });
                  setStatus("Shared. The advisor will receive an invitation.");
                } catch (e) {
                  setStatus(e instanceof Error ? e.message : "Could not share");
                }
              }}
            >
              Share
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
