"use client";
import { useEffect, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { Button, Card, CardContent, CardHeader, CardTitle, Field, Input } from "@complymate/ui";
import { api } from "@/lib/api-client";
import { useSettings } from "../_settings";

export default function BrandingPage() {
  const qc = useQueryClient();
  const { settings, save } = useSettings();
  const [color, setColor] = useState("#0F4C81");
  const [file, setFile] = useState<File | null>(null);
  useEffect(() => { if (settings?.branding?.primary_color) setColor(String(settings.branding.primary_color)); }, [settings]);
  return (
    <Card>
      <CardHeader><CardTitle>Branding on exports</CardTitle></CardHeader>
      <CardContent className="grid gap-4 md:grid-cols-2">
        <Field label="Primary colour"><Input type="color" value={color} onChange={(e) => setColor(e.target.value)} className="h-10 w-24 p-1" /></Field>
        <Field label="Logo (PNG or JPEG, under 500 KB)" hint={settings?.branding?.logo_key ? "A logo is uploaded." : undefined}>
          <input type="file" accept="image/png,image/jpeg" onChange={(e) => setFile(e.target.files?.[0] ?? null)} className="text-sm" />
        </Field>
        <div className="flex gap-2 md:col-span-2">
          <Button loading={save.isPending} onClick={() => save.mutate({ branding: { ...(settings?.branding ?? {}), primary_color: color } })}>Save colour</Button>
          <Button variant="secondary" disabled={!file} onClick={async () => {
            const form = new FormData();
            form.append("file", file!);
            await api("/tenants/current/branding/logo", { form });
            void qc.invalidateQueries({ queryKey: ["settings"] });
          }}>Upload logo</Button>
        </div>
      </CardContent>
    </Card>
  );
}
