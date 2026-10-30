# Reports and regulator pack — requirements

## User story

As a firm owner I want registers, summaries and a one-click regulator pack so I can respond to AUSTRAC quickly.

## Acceptance criteria (EARS)

1. THE SYSTEM SHALL show a compliance dashboard: clients by risk, overdue reviews, open matches, training status.
2. THE SYSTEM SHALL export client register, risk summary, screening history, program versions, training completion and audit trail as CSV/XLSX.
3. WHEN a regulator pack is requested THE SYSTEM SHALL build one ZIP with program, registers, audit trail, training records and a manifest with hashes.
4. Exports SHALL require step-up MFA and be recorded in the audit log.
5. Practice-plan firms SHALL schedule reports by email.

## Out of scope

* Legal advice. ComplyMate provides general information; firms make their own decisions.
