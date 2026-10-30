"use client";
import { use } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import type { ProgramVersion } from "@complymate/api-types";
import { PageHeader, Spinner } from "@complymate/ui";
import { ApprovalPanel } from "@/components/program/ApprovalPanel";
import { SectionEditor } from "@/components/program/SectionEditor";
import { PresenceAvatars } from "@/components/collaboration/PresenceAvatars";
import { Comments } from "@/components/collaboration/Comments";
import { ShareDialog } from "@/components/collaboration/ShareDialog";
import { ReportExportButton } from "@/components/reports/ReportExportButton";
import { get } from "@/lib/api-client";
import { usePermissions } from "@/hooks/usePermission";
import { useTenant } from "@/hooks/useTenant";

export default function VersionPage({ params }: { params: Promise<{ versionId: string }> }) {
  const { versionId } = use(params);
  const qc = useQueryClient();
  const can = usePermissions();
  const { me } = useTenant();
  const key = ["program-version", versionId];
  const { data } = useQuery({ queryKey: key, queryFn: () => get<ProgramVersion>(`/program/versions/${versionId}`), refetchInterval: 15_000 });
  if (!data) return <Spinner />;
  const refresh = () => void qc.invalidateQueries({ queryKey: key });
  const editable = can("program:update") && data.status === "draft" && !data.locked;
  return (
    <>
      <PageHeader
        title={`AML/CTF program — version ${data.version_number}`}
        description={data.change_summary ?? undefined}
        actions={
          <div className="flex items-center gap-3">
            <PresenceAvatars versionId={versionId} />
            {can("share:create") ? <ShareDialog resourceType="program_version" resourceId={versionId} /> : null}
            {can("program:export") ? (
              <>
                <ReportExportButton path={`/program/versions/${versionId}/export?format=docx`} filename="program.docx" label="DOCX" />
                <ReportExportButton path={`/program/versions/${versionId}/export?format=pdf`} filename="program.pdf" label="PDF" />
              </>
            ) : null}
          </div>
        }
      />
      <div className="grid gap-6 lg:grid-cols-[1fr_320px]">
        <div className="space-y-4">
          {data.sections.map((s) => (
            <SectionEditor key={s.id} versionId={versionId} section={s} editable={editable} currentUserId={me?.user_id} onSaved={refresh} />
          ))}
        </div>
        <div className="space-y-4">
          <ApprovalPanel version={data} onChanged={refresh} />
          <Comments resourceType="program_version" resourceId={versionId} />
        </div>
      </div>
    </>
  );
}
