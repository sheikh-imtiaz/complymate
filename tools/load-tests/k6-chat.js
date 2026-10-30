// k6 load test for "Ask the Rules" and a few read endpoints.
//   k6 run -e API=https://api.dev.complymate.example -e TOKEN=<id token> -e TENANT=<uuid> tools/load-tests/k6-chat.js
// Targets (docs: non-functional requirements): API p95 < 400 ms (non-AI), chat answer p95 well under 30 s.
import http from "k6/http";
import { check, sleep } from "k6";
import { Trend } from "k6/metrics";

const API = __ENV.API || "http://localhost:8000";
const HEADERS = {
  Authorization: `Bearer ${__ENV.TOKEN}`,
  "X-Tenant-Id": __ENV.TENANT,
  "Content-Type": "application/json",
};
const chatLatency = new Trend("chat_latency_ms", true);

export const options = {
  scenarios: {
    reads: { executor: "constant-arrival-rate", rate: 20, timeUnit: "1s", duration: "3m", preAllocatedVUs: 20, exec: "reads" },
    chat: { executor: "ramping-vus", startVUs: 1, stages: [{ duration: "1m", target: 5 }, { duration: "2m", target: 10 }], exec: "chat" },
  },
  thresholds: {
    "http_req_duration{kind:read}": ["p(95)<400"],
    "http_req_failed": ["rate<0.01"],
    chat_latency_ms: ["p(95)<30000"],
  },
};

const QUESTIONS = [
  "When must we lodge a suspicious matter report?",
  "What is a beneficial owner?",
  "When is enhanced customer due diligence required?",
  "How long must we keep records?",
];

export function reads() {
  for (const path of ["/clients?limit=20", "/reports/dashboard", "/tasks", "/notifications/unread-count"]) {
    const res = http.get(`${API}${path}`, { headers: HEADERS, tags: { kind: "read" } });
    check(res, { "read ok": (r) => r.status === 200 });
  }
}

export function chat() {
  const q = QUESTIONS[Math.floor(Math.random() * QUESTIONS.length)];
  const res = http.post(`${API}/chat`, JSON.stringify({ message: q, stream: false }), { headers: HEADERS, timeout: "60s", tags: { kind: "chat" } });
  chatLatency.add(res.timings.duration);
  check(res, {
    "chat ok": (r) => r.status === 200,
    "has citations": (r) => r.status === 200 && JSON.parse(r.body).citations.length > 0,
  });
  sleep(2);
}
