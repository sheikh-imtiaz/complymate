# Ask the Rules chat — requirements

## User story

As a staff member I want sourced answers about AML/CTF rules so I can act correctly without legal advice.

## Acceptance criteria (EARS)

1. THE SYSTEM SHALL answer only from rule-library sources and show title, publisher, link and last-checked date for each citation.
2. THE SYSTEM SHALL stream the first token in under 3 seconds (WebSocket).
3. THE SYSTEM SHALL read firm context (client risk) only through permission-checked tools in the user's RLS session.
4. WHEN a request seeks to tip off a client THE SYSTEM SHALL refuse and explain the offence.
5. THE SYSTEM SHALL add a not-legal-advice disclaimer and redact ID numbers from answers.
6. Feedback marked wrong SHALL go to the Platform AI quality review queue.
7. THE SYSTEM SHALL record model, prompt version, sources, tool calls and cost for each answer.

## Out of scope

* Legal advice. ComplyMate provides general information; firms make their own decisions.
