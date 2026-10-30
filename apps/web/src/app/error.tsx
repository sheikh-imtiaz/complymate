"use client";
import { Button } from "@complymate/ui";

export default function GlobalError({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-3 p-6 text-center">
      <h1 className="text-2xl font-semibold">Something went wrong</h1>
      <p className="max-w-md text-slate-500">{error.message || "An unexpected error occurred."}</p>
      {error.digest ? <p className="text-xs text-slate-400">Reference: {error.digest}</p> : null}
      <Button onClick={reset}>Try again</Button>
    </main>
  );
}
