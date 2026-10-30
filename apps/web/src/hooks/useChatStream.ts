"use client";
import { useCallback, useEffect, useRef, useState } from "react";
import { openChatSocket, type ChatEvent, type Citation } from "@/lib/ws";

export interface ChatTurn {
  id: string;
  role: "user" | "assistant";
  content: string;
  citations: Citation[];
  messageId?: string;
  blocked?: boolean;
  pending?: boolean;
}

/** Streams "Ask the Rules" answers over WebSocket. Tokens arrive in order; `done` carries the saved message id. */
export function useChatStream() {
  const [turns, setTurns] = useState<ChatTurn[]>([]);
  const [sessionId, setSessionId] = useState<string | undefined>();
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const socket = useRef<Awaited<ReturnType<typeof openChatSocket>> | null>(null);

  const onEvent = useCallback((e: ChatEvent) => {
    setTurns((prev) => {
      const next = [...prev];
      const last = next[next.length - 1];
      if (!last || last.role !== "assistant") return prev;
      switch (e.type) {
        case "token":
          last.content += e.data;
          break;
        case "replace":
          last.content = e.data;
          break;
        case "citations":
          last.citations = e.data;
          break;
        case "blocked":
          last.blocked = true;
          break;
        case "done":
          last.content = e.data.answer;
          last.citations = e.data.citations;
          last.messageId = e.data.message_id;
          last.pending = false;
          break;
        case "error":
          last.content = e.data.message;
          last.pending = false;
          break;
        default:
          return prev;
      }
      return next.map((t, i) => (i === next.length - 1 ? { ...last } : t));
    });
    if (e.type === "done") {
      setSessionId(e.data.session_id);
      setBusy(false);
    }
    if (e.type === "error") {
      setError(e.data.message);
      setBusy(false);
    }
  }, []);

  useEffect(() => () => socket.current?.close(), []);

  const ask = useCallback(
    async (question: string, clientId?: string) => {
      setError(null);
      setBusy(true);
      setTurns((t) => [
        ...t,
        { id: crypto.randomUUID(), role: "user", content: question, citations: [] },
        { id: crypto.randomUUID(), role: "assistant", content: "", citations: [], pending: true },
      ]);
      try {
        if (!socket.current) socket.current = await openChatSocket(onEvent);
        await socket.current.send(question, sessionId, clientId);
      } catch (err) {
        socket.current = null;
        setError(err instanceof Error ? err.message : "Chat failed");
        setBusy(false);
      }
    },
    [onEvent, sessionId],
  );

  return { turns, ask, busy, error, sessionId, reset: () => { setTurns([]); setSessionId(undefined); } };
}
