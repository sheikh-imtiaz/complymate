"use client";
// Chat WebSocket. "native" = FastAPI /ws/chat (local, Azure). "apigw" = AWS API Gateway WebSocket, where the
// token is checked on $connect (query string) and sent again with every message.
import { getTenantId, getToken } from "./auth";

export type ChatEvent =
  | { type: "token"; data: string }
  | { type: "replace"; data: string }
  | { type: "citations"; data: Citation[] }
  | { type: "blocked"; data: { category: string } }
  | { type: "notice"; data: string }
  | { type: "done"; data: { session_id: string; message_id: string; answer: string; citations: Citation[]; model: string } }
  | { type: "error"; data: { code: string; message: string } }
  | { type: "pong" };

export interface Citation {
  ref: string;
  title: string;
  url: string | null;
  publisher: string;
  heading: string | null;
  last_checked_at: string | null;
  score: number;
}

const WS_URL = process.env.NEXT_PUBLIC_WS_URL ?? "ws://localhost:8000/ws/chat";
const MODE = process.env.NEXT_PUBLIC_WS_MODE ?? "native";

export async function openChatSocket(onEvent: (e: ChatEvent) => void): Promise<{
  send: (message: string, sessionId?: string, clientId?: string) => Promise<void>;
  close: () => void;
}> {
  const token = (await getToken()) ?? "";
  const tenant = getTenantId() ?? "";
  const qs = new URLSearchParams({ token, ...(MODE === "native" ? { tenant } : {}) });
  const socket = new WebSocket(`${WS_URL}?${qs.toString()}`);
  await new Promise<void>((resolve, reject) => {
    socket.onopen = () => resolve();
    socket.onerror = () => reject(new Error("Could not connect to chat"));
  });
  socket.onmessage = (msg) => {
    try {
      onEvent(JSON.parse(msg.data as string) as ChatEvent);
    } catch {
      /* ignore malformed frames */
    }
  };
  const ping = window.setInterval(() => socket.readyState === WebSocket.OPEN && socket.send(JSON.stringify({ action: "ping" })), 240_000);
  return {
    send: async (message, sessionId, clientId) => {
      socket.send(
        JSON.stringify({
          action: "chat",
          message,
          session_id: sessionId,
          client_id: clientId,
          token: await getToken(),
          tenant_id: getTenantId(),
        }),
      );
    },
    close: () => {
      window.clearInterval(ping);
      socket.close();
    },
  };
}
