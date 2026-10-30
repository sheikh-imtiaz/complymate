"use client";
import { useState } from "react";
import { Alert, Button, Dialog, DialogContent, Field, Select, Textarea } from "@complymate/ui";
import { post } from "@/lib/api-client";
import type { ScreeningMatch } from "./MatchCard";

export function MatchReviewDialog({ match, onClose, onDone }: { match: ScreeningMatch | null; onClose: () => void; onDone: () => void }) {
  const [decision, setDecision] = useState("false_positive");
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  if (!match) return null;
  return (
    <Dialog open onOpenChange={(o) => !o && onClose()}>
      <DialogContent title="Review screening match" description={`${match.subject_name} vs ${match.entry.primary_name}`}>
        <div className="grid gap-4">
          <Field label="Decision">
            <Select value={decision} onChange={(e) => setDecision(e.target.value)}>
              <option value="false_positive">False positive — different person/entity</option>
              <option value="needs_info">Needs more information</option>
              <option value="true_match">True match (compliance officer only)</option>
            </Select>
          </Field>
          <Field label="Reason" hint="Record what you checked (date of birth, nationality, ID documents).">
            <Textarea value={note} onChange={(e) => setNote(e.target.value)} />
          </Field>
          {decision === "true_match" ? (
            <Alert tone="danger" title="Confirmed sanctions match">Do not provide services or deal with assets. Decline the client and consider a suspicious matter report. Do not tell the client why.</Alert>
          ) : null}
          {error ? <p className="text-sm text-red-600">{error}</p> : null}
          <div className="flex justify-end gap-2">
            <Button variant="secondary" onClick={onClose}>Cancel</Button>
            <Button
              loading={busy}
              disabled={note.trim().length < 3}
              onClick={async () => {
                setBusy(true);
                try {
                  await post(`/screening/matches/${match.id}/review`, { decision, note });
                  onDone();
                } catch (e) {
                  setError(e instanceof Error ? e.message : "Could not save");
                } finally {
                  setBusy(false);
                }
              }}
            >
              Save decision
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
