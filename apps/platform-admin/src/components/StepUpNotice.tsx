"use client";
import { useEffect, useState } from "react";
import { Button, Dialog, DialogContent } from "@complymate/ui";
import { stepUp } from "@/lib/auth";

export function StepUpNotice() {
  const [open, setOpen] = useState(false);
  useEffect(() => {
    const h = () => setOpen(true);
    window.addEventListener("cm:step-up", h);
    return () => window.removeEventListener("cm:step-up", h);
  }, []);
  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogContent title="Re-verify with MFA" description="Impersonation and break-glass actions need MFA in the last 10 minutes.">
        <div className="flex justify-end"><Button onClick={() => void stepUp()}>Verify</Button></div>
      </DialogContent>
    </Dialog>
  );
}
