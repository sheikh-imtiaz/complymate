"use client";
import { Suspense, use } from "react";
import { useSearchParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { Alert, PageHeader, Spinner } from "@complymate/ui";
import { VersionDiff, type CompareSection } from "@/components/program/VersionDiff";
import { get } from "@/lib/api-client";

function Compare({ versionId }: { versionId: string }) {
  const other = useSearchParams().get("with");
  const { data } = useQuery({
    queryKey: ["compare", versionId, other],
    queryFn: () => get<CompareSection[]>(`/program/versions/${other}/compare/${versionId}`),
    enabled: !!other,
  });
  if (!other) return <Alert tone="warning">Choose a version to compare with.</Alert>;
  return data ? <VersionDiff sections={data} /> : <Spinner />;
}

export default function ComparePage({ params }: { params: Promise<{ versionId: string }> }) {
  const { versionId } = use(params);
  return (
    <>
      <PageHeader title="Compare versions" description="Green lines were added, red lines removed, compared with the approved version." />
      <Suspense><Compare versionId={versionId} /></Suspense>
    </>
  );
}
