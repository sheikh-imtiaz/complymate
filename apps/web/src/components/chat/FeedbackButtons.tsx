"use client";
import { useState } from "react";
import { ThumbsDown, ThumbsUp } from "lucide-react";
import { Button } from "@complymate/ui";
import { post } from "@/lib/api-client";

export function FeedbackButtons({ messageId }: { messageId: string }) {
  const [sent, setSent] = useState<string | null>(null);
  async function send(rating: "helpful" | "wrong") {
    const comment = rating === "wrong" ? window.prompt("What was wrong? (optional)") ?? undefined : undefined;
    await post(`/chat/messages/${messageId}/feedback`, { rating, comment });
    setSent(rating);
  }
  if (sent) return <span className="text-xs text-slate-500">Thanks — {sent === "wrong" ? "sent for review" : "feedback saved"}.</span>;
  return (
    <div className="flex gap-1">
      <Button variant="ghost" size="sm" onClick={() => void send("helpful")} aria-label="Helpful"><ThumbsUp className="h-3.5 w-3.5" /></Button>
      <Button variant="ghost" size="sm" onClick={() => void send("wrong")} aria-label="Wrong"><ThumbsDown className="h-3.5 w-3.5" /></Button>
    </div>
  );
}
