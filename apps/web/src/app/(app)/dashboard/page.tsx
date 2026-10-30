"use client";
import { useQuery } from "@tanstack/react-query";
import { PageHeader, Spinner } from "@complymate/ui";
import { ComplianceDashboard, type Dashboard } from "@/components/reports/ComplianceDashboard";
import { get } from "@/lib/api-client";
import { useTenant } from "@/hooks/useTenant";

export default function DashboardPage() {
  const { tenantName } = useTenant();
  const { data, isLoading } = useQuery({ queryKey: ["dashboard"], queryFn: () => get<Dashboard>("/reports/dashboard") });
  return (
    <>
      <PageHeader title="Compliance dashboard" description={tenantName} />
      {isLoading || !data ? <Spinner /> : <ComplianceDashboard data={data} />}
    </>
  );
}
