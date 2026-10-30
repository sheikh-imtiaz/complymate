# AML/CTF Program Builder — requirements

## User story

As an AMLCO I want a guided interview and agent-drafted sections with citations so I can produce an approvable AML/CTF program quickly.

## Acceptance criteria (EARS)

1. THE SYSTEM SHALL save interview answers as they are typed.
2. WHEN drafting is requested THE SYSTEM SHALL draft each section from interview answers and rule-library sources, with citations, as a suggestion.
3. WHEN a user accepts or rejects a suggestion THE SYSTEM SHALL record the decision in the audit log.
4. WHILE a section is being edited THE SYSTEM SHALL lock it for other users (5-minute lease) and show presence.
5. THE SYSTEM SHALL enforce draft → AMLCO review → Senior Manager/Owner sign-off, and the submitter SHALL NOT sign off.
6. WHEN a version is approved THE SYSTEM SHALL lock it, snapshot it and schedule the annual review reminder.
7. THE SYSTEM SHALL export DOCX and PDF with the firm logo and colours, and compare any two versions.

## Out of scope

* Legal advice. ComplyMate provides general information; firms make their own decisions.
