"use client";
import { useEffect, useState } from "react";
import { Alert, Button, Card, CardContent, CardHeader, CardTitle, Field, Input } from "@complymate/ui";
import { useSettings } from "../_settings";

export default function RetentionPage() {
  const { settings, save } = useSettings();
  const [years, setYears] = useState(7);
  useEffect(() => { if (settings) setYears(settings.retention_years); }, [settings]);
  return (
    <Card>
      <CardHeader><CardTitle>Data retention</CardTitle></CardHeader>
      <CardContent className="space-y-4">
        <Alert tone="info">AML/CTF records must be kept for at least 7 years. ComplyMate never deletes records earlier, and the audit archive is locked (write-once) for 7 years.</Alert>
        <Field label="Keep client records after the relationship ends (years)"><Input type="number" min={7} max={50} value={years} onChange={(e) => setYears(Number(e.target.value))} className="w-32" /></Field>
        <Button loading={save.isPending} onClick={() => save.mutate({ retention_years: years })}>Save</Button>
        {save.error ? <Alert tone="danger">{(save.error as Error).message}</Alert> : null}
      </CardContent>
    </Card>
  );
}
