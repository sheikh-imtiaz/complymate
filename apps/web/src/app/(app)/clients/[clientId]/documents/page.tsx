"use client";
import { use, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import type { Document } from "@complymate/api-types";
import { Badge, Button, Card, CardContent, CardHeader, CardTitle, EmptyState, Input } from "@complymate/ui";
import { DocumentUploader } from "@/components/clients/DocumentUploader";
import { download, get, post } from "@/lib/api-client";
import { formatDateTime } from "@/lib/format";
import { usePermissions } from "@/hooks/usePermission";

function OcrConfirm({ doc, onDone }: { doc: Document; onDone: () => void }) {
  const [fields, setFields] = useState<Record<string, string>>(Object.fromEntries(Object.entries(doc.ocr_fields).map(([k, v]) => [k, String(v)])));
  const keys = Array.from(new Set([...Object.keys(fields), "full_name", "date_of_birth", "document_number", "expiry_date"]));
  return (
    <div className="mt-3 grid gap-2 rounded-lg bg-slate-50 p-3">
      <p className="text-xs font-semibold text-slate-600">Check the extracted details against the document, correct them, then confirm.</p>
      {keys.map((k) => (
        <label key={k} className="grid grid-cols-3 items-center gap-2 text-sm">
          <span className="text-slate-500">{k.replace(/_/g, " ")}</span>
          <Input className="col-span-2" value={fields[k] ?? ""} onChange={(e) => setFields({ ...fields, [k]: e.target.value })} />
        </label>
      ))}
      <Button size="sm" onClick={async () => { await post(`/documents/${doc.id}/confirm`, { fields, apply_to_client: true }); onDone(); }}>Confirm details</Button>
    </div>
  );
}

export default function DocumentsPage({ params }: { params: Promise<{ clientId: string }> }) {
  const { clientId } = use(params);
  const qc = useQueryClient();
  const can = usePermissions();
  const key = ["documents", clientId];
  const { data = [] } = useQuery({ queryKey: key, queryFn: () => get<Document[]>(`/clients/${clientId}/documents`), refetchInterval: 10_000 });
  const refresh = () => void qc.invalidateQueries({ queryKey: key });
  return (
    <div className="space-y-6">
      {can("document:create") ? <DocumentUploader clientId={clientId} onUploaded={refresh} /> : null}
      {!data.length ? <EmptyState title="No documents" description="Upload ID documents or company extracts." /> : null}
      {data.map((d) => (
        <Card key={d.id}>
          <CardHeader className="flex-row items-center justify-between">
            <CardTitle>{d.doc_type.replace(/_/g, " ")} <span className="text-sm font-normal text-slate-500">· {d.filename}</span></CardTitle>
            <div className="flex items-center gap-2">
              <Badge tone={d.ocr_confirmed ? "success" : d.ocr_status === "failed" ? "danger" : "info"}>{d.ocr_confirmed ? "Confirmed" : `OCR ${d.ocr_status}`}</Badge>
              {can("document:read") ? <Button size="sm" variant="secondary" onClick={() => void download(`/documents/${d.id}/download`, d.filename)}>View</Button> : null}
            </div>
          </CardHeader>
          <CardContent className="text-sm">
            <p className="text-xs text-slate-500">Uploaded {formatDateTime(d.created_at)} · {(d.size_bytes / 1024).toFixed(0)} KB · SHA-256 {d.sha256.slice(0, 12)}…</p>
            {d.ocr_confirmed || !can("client:update") ? (
              <dl className="mt-2 grid grid-cols-2 gap-1">{Object.entries(d.ocr_fields).map(([k, v]) => <div key={k} className="contents"><dt className="text-slate-500">{k.replace(/_/g, " ")}</dt><dd>{String(v)}</dd></div>)}</dl>
            ) : d.ocr_status === "done" || d.ocr_status === "failed" ? <OcrConfirm doc={d} onDone={refresh} /> : null}
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
