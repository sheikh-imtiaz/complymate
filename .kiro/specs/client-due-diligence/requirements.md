# Client due diligence (CDD) — requirements

## User story

As a staff member I want to onboard clients with owners, ID documents and a clear risk rating so the firm meets its CDD obligations.

## Acceptance criteria (EARS)

1. THE SYSTEM SHALL support individual, company, trust and partnership clients.
2. THE SYSTEM SHALL calculate effective ownership through layers and flag beneficial owners (≥25% or control).
3. WHEN a document is uploaded THE SYSTEM SHALL encrypt it with the tenant data key, extract fields by OCR and require a person to confirm them.
4. THE SYSTEM SHALL score risk deterministically from versioned YAML rules, showing every reason.
5. WHEN risk is high THE SYSTEM SHALL create EDD tasks and require a second person to approve the client.
6. THE SYSTEM SHALL set the next review date by risk level and create review tasks before it is due.
7. Auditors SHALL see masked document fields and SHALL NOT download documents.

## Out of scope

* Legal advice. ComplyMate provides general information; firms make their own decisions.
