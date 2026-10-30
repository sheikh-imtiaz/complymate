"use client";
import { Input, Select } from "@complymate/ui";

export interface AuditFilterValues { action?: string; resource_type?: string; resource_id?: string; date_from?: string; date_to?: string }

const ACTIONS = ["create", "update", "delete", "approve", "reject", "submit", "export", "login", "role_change", "permission_change", "screen", "decide", "ai_suggestion", "ai_accepted", "ai_rejected", "view_sensitive"];

export function AuditFilters({ value, onChange }: { value: AuditFilterValues; onChange: (v: AuditFilterValues) => void }) {
  return (
    <div className="grid gap-3 md:grid-cols-5">
      <Select value={value.action ?? ""} onChange={(e) => onChange({ ...value, action: e.target.value || undefined })} aria-label="Action">
        <option value="">All actions</option>
        {ACTIONS.map((a) => <option key={a} value={a}>{a.replace(/_/g, " ")}</option>)}
      </Select>
      <Input placeholder="Resource type (e.g. client)" value={value.resource_type ?? ""} onChange={(e) => onChange({ ...value, resource_type: e.target.value || undefined })} />
      <Input placeholder="Resource id" value={value.resource_id ?? ""} onChange={(e) => onChange({ ...value, resource_id: e.target.value || undefined })} />
      <Input type="date" value={value.date_from ?? ""} onChange={(e) => onChange({ ...value, date_from: e.target.value || undefined })} aria-label="From" />
      <Input type="date" value={value.date_to ?? ""} onChange={(e) => onChange({ ...value, date_to: e.target.value || undefined })} aria-label="To" />
    </div>
  );
}
