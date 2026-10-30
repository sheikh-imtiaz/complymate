"use client";
import { useState } from "react";
import { Download } from "lucide-react";
import { Button } from "@complymate/ui";
import { download } from "@/lib/api-client";

export function ReportExportButton({ path, filename, label = "Export" }: { path: string; filename: string; label?: string }) {
  const [busy, setBusy] = useState(false);
  return (
    <Button
      variant="secondary"
      size="sm"
      loading={busy}
      onClick={async () => {
        setBusy(true);
        try {
          await download(path, filename);
        } finally {
          setBusy(false);
        }
      }}
    >
      <Download className="h-4 w-4" />{label}
    </Button>
  );
}
