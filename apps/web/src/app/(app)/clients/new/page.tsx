"use client";
import { useRouter } from "next/navigation";
import { useMutation } from "@tanstack/react-query";
import { Alert, Card, CardContent, PageHeader } from "@complymate/ui";
import { ClientForm, type ClientFormValues } from "@/components/clients/ClientForm";
import { RequirePermission } from "@/components/auth/RequirePermission";
import { post } from "@/lib/api-client";

export default function NewClientPage() {
  const router = useRouter();
  const create = useMutation({
    mutationFn: (v: ClientFormValues) => post<{ id: string }>("/clients", v),
    onSuccess: (c) => router.push(`/clients/${c.id}/owners`),
  });
  return (
    <RequirePermission permission="client:create">
      <PageHeader title="New client" description="Record who the client is. Next you'll add owners, upload ID and run screening." />
      <Card><CardContent className="pt-5"><ClientForm onSubmit={(v) => create.mutate(v)} submitting={create.isPending} /></CardContent></Card>
      {create.error ? <Alert tone="danger" className="mt-4">{(create.error as Error).message}</Alert> : null}
    </RequirePermission>
  );
}
