"use client";
import { useRouter } from "next/navigation";
import { PageHeader } from "@complymate/ui";
import { InterviewWizard } from "@/components/program/InterviewWizard";

export default function InterviewPage() {
  const router = useRouter();
  return (
    <>
      <PageHeader title="Program interview" description="About 20–30 questions. Answers save as you go and feed the agent's drafts." />
      <InterviewWizard onFinished={() => router.push("/program")} />
    </>
  );
}
