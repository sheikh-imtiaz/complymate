"use client";
import { flexRender, getCoreRowModel, useReactTable, type ColumnDef } from "@tanstack/react-table";
import type { AuditEvent } from "@complymate/api-types";
import { Badge, Table, TBody, TD, TH, THead, TR } from "@complymate/ui";
import { formatDateTime, humanize } from "@/lib/format";

const columns: ColumnDef<AuditEvent>[] = [
  { header: "When", accessorKey: "occurred_at", cell: (c) => formatDateTime(c.getValue<string>()) },
  { header: "Action", accessorKey: "action", cell: (c) => <Badge tone={["export", "role_change", "view_sensitive"].includes(c.getValue<string>()) ? "warning" : "neutral"}>{humanize(c.getValue<string>())}</Badge> },
  { header: "Resource", cell: ({ row }) => `${humanize(row.original.resource_type)}${row.original.resource_id ? ` · ${row.original.resource_id.slice(0, 8)}` : ""}` },
  { header: "Actor", accessorKey: "actor_role", cell: (c) => humanize(c.getValue<string>()) },
  { header: "Hash", accessorKey: "hash", cell: (c) => <code className="text-xs text-slate-400">{c.getValue<string>().slice(0, 10)}…</code> },
];

export function AuditTable({ data, onSelect }: { data: AuditEvent[]; onSelect: (e: AuditEvent) => void }) {
  const table = useReactTable({ data, columns, getCoreRowModel: getCoreRowModel() });
  return (
    <Table>
      <THead>
        {table.getHeaderGroups().map((hg) => (
          <TR key={hg.id}>{hg.headers.map((h) => <TH key={h.id}>{flexRender(h.column.columnDef.header, h.getContext())}</TH>)}</TR>
        ))}
      </THead>
      <TBody>
        {table.getRowModel().rows.map((row) => (
          <TR key={row.id} className="cursor-pointer" onClick={() => onSelect(row.original)}>
            {row.getVisibleCells().map((cell) => <TD key={cell.id}>{flexRender(cell.column.columnDef.cell, cell.getContext())}</TD>)}
          </TR>
        ))}
      </TBody>
    </Table>
  );
}
