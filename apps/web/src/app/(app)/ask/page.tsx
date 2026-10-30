"use client";
import { PageHeader } from "@complymate/ui";
import { ChatPanel } from "@/components/chat/ChatPanel";
import { RequirePermission } from "@/components/auth/RequirePermission";

export default function AskPage() {
  return (
    <RequirePermission permission="chat:use">
      <PageHeader title="Ask the Rules" description="Answers from AUSTRAC / DIA guidance, with citations." />
      <ChatPanel />
    </RequirePermission>
  );
}
