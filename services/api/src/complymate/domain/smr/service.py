"""Suspicious Matter Reporting. Staff raise a draft concern; the AMLCO reviews, adds facts and decides.
The agent may structure fields but never submits. Export is for manual lodgement in AUSTRAC Online."""

from __future__ import annotations

import csv
import io
import json
from datetime import UTC, datetime
from typing import Any

from complymate.domain.errors import Conflict

TIPPING_OFF_WARNING = (
    "Tipping-off warning: it is an offence to disclose to the client or any other person that a suspicious "
    "matter report has been or may be made, or information from which that could be inferred. "
    "Do not discuss this matter outside the compliance team."
)

STATUSES = ("draft", "under_review", "decided_report", "decided_no_report", "exported")
TRANSITIONS = {
    "draft": {"under_review"},
    "under_review": {"decided_report", "decided_no_report", "draft"},
    "decided_report": {"exported"},
    "decided_no_report": set(),
    "exported": set(),
}

SUSPICION_CATEGORIES = [
    "unusual_transaction",
    "structuring",
    "identity_concerns",
    "source_of_funds",
    "third_party_payments",
    "sanctions",
    "terrorism_financing",
    "tax_evasion",
    "fraud",
    "proceeds_of_crime",
    "other",
]

# Field names follow the AUSTRAC SMR form sections (manual lodgement).
AUSTRAC_FIELDS = [
    "reporting_entity_name",
    "reporting_entity_abn",
    "suspicion_formed_date",
    "grounds_for_suspicion",
    "suspicion_categories",
    "subject_full_name",
    "subject_date_of_birth",
    "subject_address",
    "subject_identifiers",
    "designated_service",
    "transaction_date",
    "transaction_amount_aud",
    "transaction_type",
    "other_parties",
    "related_reports",
    "contact_officer",
]


def assert_transition(current: str, new: str) -> None:
    if new not in TRANSITIONS[current]:
        raise Conflict(f"cannot move SMR from {current} to {new}")


def next_reference(year: int, count: int) -> str:
    return f"SMR-{year}-{count + 1:04d}"


def austrac_export(case: dict[str, Any], firm: dict[str, Any], client: dict[str, Any] | None) -> dict[str, Any]:
    fields = dict(case.get("austrac_fields") or {})
    fields.setdefault("reporting_entity_name", firm.get("name"))
    fields.setdefault("reporting_entity_abn", firm.get("abn") or firm.get("nzbn"))
    fields.setdefault(
        "suspicion_formed_date",
        (case.get("decided_at") or datetime.now(UTC)).date().isoformat()
        if isinstance(case.get("decided_at"), datetime)
        else datetime.now(UTC).date().isoformat(),
    )
    fields.setdefault("grounds_for_suspicion", case.get("grounds"))
    fields.setdefault("suspicion_categories", ", ".join(case.get("suspicion_categories") or []))
    if client:
        fields.setdefault("subject_full_name", client.get("display_name"))
        fields.setdefault("subject_date_of_birth", str(client.get("date_of_birth") or ""))
    return {k: fields.get(k, "") for k in AUSTRAC_FIELDS} | {"reference": case.get("reference")}


def export_files(payload: dict[str, Any]) -> dict[str, bytes]:
    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerow(["field", "value"])
    for k, v in payload.items():
        writer.writerow([k, v if not isinstance(v, list | dict) else json.dumps(v)])
    return {
        "smr.json": json.dumps(payload, indent=2, default=str).encode(),
        "smr.csv": out.getvalue().encode(),
        "README.txt": (
            "Lodge this SMR manually in AUSTRAC Online within the required timeframe (24 hours for terrorism "
            "financing, 3 business days otherwise). ComplyMate never submits reports.\n\n" + TIPPING_OFF_WARNING
        ).encode(),
    }
