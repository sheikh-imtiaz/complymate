"use client";
import { useEffect, useState } from "react";
import { ShieldCheck } from "lucide-react";
import { Button, Dialog, DialogContent } from "@complymate/ui";
import { stepUp } from "@/lib/auth";

/** Sensitive actions (approve high-risk client, decide an SMR, change roles, export) need MFA in the last
 * 10 minutes. The API answers 401 step_up_mfa_required; this dialog asks the user to re-authenticate. */
export function StepUpMfaDialog() {
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  useEffect(() => {
    const handler = () => setOpen(true);
    window.addEventListener("cm:step-up", handler);
    return () => window.removeEventListener("cm:step-up", handler);
  }, []);
  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogContent title="Confirm it's you" description="This action needs a fresh multi-factor sign-in.">
        <div className="flex items-start gap-3 rounded-lg bg-brand-50 p-3 text-sm text-brand-700">
          <ShieldCheck className="mt-0.5 h-5 w-5" />
          <p>For approvals, suspicious matter decisions, role changes and exports we ask you to verify with MFA again. Then retry the action.</p>
        </div>
        <div className="mt-4 flex justify-end gap-2">
          <Button variant="secondary" onClick={() => setOpen(false)}>Cancel</Button>
          <Button
            loading={busy}
            onClick={async () => {
              setBusy(true);
              await stepUp();
              setBusy(false);
              setOpen(false);
            }}
          >
            Verify with MFA
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
