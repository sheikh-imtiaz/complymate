"use client";
import { useState } from "react";
import { Upload } from "lucide-react";
import { Button, Select } from "@complymate/ui";
import { api } from "@/lib/api-client";

const DOC_TYPES = ["passport", "drivers_licence", "birth_certificate", "medicare_card", "proof_of_address", "asic_extract", "certificate_of_registration", "trust_deed", "partnership_agreement", "source_of_funds", "other"];

export function DocumentUploader({ clientId, onUploaded }: { clientId: string; onUploaded: () => void }) {
  const [docType, setDocType] = useState("passport");
  const [file, setFile] = useState<File | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function upload() {
    if (!file) return;
    if (file.size > 5 * 1024 * 1024) {
      setError("Files must be 5 MB or smaller.");
      return;
    }
    setBusy(true);
    setError(null);
    const form = new FormData();
    form.append("file", file);
    form.append("doc_type", docType);
    try {
      await api(`/clients/${clientId}/documents`, { form });
      setFile(null);
      onUploaded();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Upload failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex flex-col gap-3 rounded-lg border border-dashed border-slate-300 p-4">
      <div className="flex flex-wrap items-center gap-3">
        <Select value={docType} onChange={(e) => setDocType(e.target.value)} className="w-56">
          {DOC_TYPES.map((t) => <option key={t} value={t}>{t.replace(/_/g, " ")}</option>)}
        </Select>
        <input type="file" accept="image/jpeg,image/png,application/pdf" onChange={(e) => setFile(e.target.files?.[0] ?? null)} className="text-sm" />
        <Button onClick={upload} disabled={!file} loading={busy}><Upload className="h-4 w-4" />Upload</Button>
      </div>
      <p className="text-xs text-slate-500">Documents are encrypted with your firm&apos;s key. Text is extracted automatically; you confirm it before it is used.</p>
      {error ? <p className="text-sm text-red-600">{error}</p> : null}
    </div>
  );
}
