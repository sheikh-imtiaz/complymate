# Sanctions and PEP screening — requirements

## User story

As an AMLCO I want every client and owner screened at onboarding and nightly so I never service a sanctioned person.

## Acceptance criteria (EARS)

1. THE SYSTEM SHALL load the DFAT consolidated list (AU) and NZ list into versioned watchlists, and re-screen all active clients when lists change.
2. THE SYSTEM SHALL match names with fuzzy and phonetic matching and DOB adjustment, reporting a 0-100 score.
3. WHEN a possible match is found THE SYSTEM SHALL queue it for review and notify the AMLCO.
4. THE SYSTEM SHALL keep false-positive decisions so the same name/entry is not raised again.
5. ONLY the AMLCO SHALL confirm a true match; a true match SHALL block approval and prompt an SMR task.
6. THE SYSTEM SHALL produce a screening certificate per client.
7. PEP screening SHALL start with a manual declaration (provider integration later).

## Out of scope

* Legal advice. ComplyMate provides general information; firms make their own decisions.
