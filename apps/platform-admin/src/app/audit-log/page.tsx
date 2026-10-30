"use client";
import { useQuery } from "@tanstack/react-query";
import type { AuditEvent } from "@complymate/api-types";
import { Badge, Card, CardContent, PageHeader, Table, TBody, TD, TH, THead, TR } from "@complymate/ui";
import { get } from "@/lib/api-client";

export default function PlatformAuditLog() {
  const { data = [] } = useQuery({ queryKey: ["platform-audit"], queryFn: () => get<AuditEvent[]>("/platform/audit?limit=500") });
  return (
    <>
      <PageHeader title="Platform audit log" description="Staff actions: tenant changes, flags, content, support access and break-glass." />
      <Card>
        <CardContent className="pt-5">
          <Table>
            <THead><TR><TH>When</TH><TH>Actor</TH><TH>Action</TH><TH>Resource</TH><TH>Reason</TH></TR></THead>
            <TBody>{data.map((e) => (
              <TR key={e.id}>
                <TD>{new Date(e.occurred_at).toLocaleString("en-AU")}</TD><TD>{e.actor_role}</TD>
                <TD><Badge tone={["break_glass", "impersonation_start"].includes(e.action) ? "danger" : "neutral"}>{e.action}</Badge></TD>
                <TD>{e.resource_type} {e.resource_id ? `· ${e.resource_id.slice(0, 12)}` : ""}</TD><TD>{e.reason ?? "—"}</TD>
              </TR>
            ))}</TBody>
          </Table>
        </CardContent>
      </Card>
    </>
  );
}
