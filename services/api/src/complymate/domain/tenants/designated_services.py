"""Designated services check: tells a firm whether AML/CTF obligations apply.

AU: Tranche 2 reforms (AML/CTF Amendment Act 2024) bring lawyers, accountants, conveyancers, real estate
professionals, trust and company service providers and dealers in precious stones/metals into the regime from
1 July 2026 (real estate, legal, accounting, TCSP services) — general information only.
NZ: these sectors are already reporting entities under the AML/CFT Act 2009 (DIA supervises most of them).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ServiceQuestion:
    code: str
    question: str
    designated: bool
    sector: str


QUESTIONS: list[ServiceQuestion] = [
    ServiceQuestion(
        "real_estate_transaction",
        "Do you buy, sell or transfer real estate for clients (as agent, lawyer or conveyancer)?",
        True,
        "real_estate",
    ),
    ServiceQuestion(
        "handling_client_money",
        "Do you receive, hold or control client money or property (e.g. trust account)?",
        True,
        "legal_accounting",
    ),
    ServiceQuestion(
        "company_or_trust_formation",
        "Do you create or restructure companies, trusts or other legal arrangements?",
        True,
        "tcsp",
    ),
    ServiceQuestion(
        "nominee_director_or_shareholder",
        "Do you act (or arrange for someone to act) as a nominee director, shareholder or trustee?",
        True,
        "tcsp",
    ),
    ServiceQuestion(
        "registered_office_services",
        "Do you provide a registered office or business address for a company or trust?",
        True,
        "tcsp",
    ),
    ServiceQuestion(
        "selling_shareholdings_or_businesses",
        "Do you help clients buy or sell a business, shares or other securities?",
        True,
        "legal_accounting",
    ),
    ServiceQuestion(
        "managing_client_accounts",
        "Do you manage client bank, savings or securities accounts?",
        True,
        "legal_accounting",
    ),
    ServiceQuestion(
        "precious_metals_stones_cash",
        "Do you buy or sell precious metals, stones or jewellery for A$10,000 or more in cash?",
        True,
        "dealers",
    ),
    ServiceQuestion(
        "tax_and_bookkeeping_only", "Do you only provide tax returns, bookkeeping or general advice?", False, "other"
    ),
    ServiceQuestion(
        "litigation_only", "Do you only provide litigation or dispute resolution services?", False, "other"
    ),
]

DESIGNATED_CODES = frozenset(q.code for q in QUESTIONS if q.designated)


@dataclass(frozen=True)
class ApplicabilityResult:
    applies: bool
    jurisdiction: str
    designated_services: list[str]
    explanation: str


def check_applicability(jurisdiction: str, services: list[str]) -> ApplicabilityResult:
    designated = sorted(set(services) & DESIGNATED_CODES)
    if not designated:
        return ApplicabilityResult(
            False,
            jurisdiction,
            [],
            "Based on your answers you may not provide designated services. Keep your account to monitor guidance; "
            "your obligations change if you start providing any of these services.",
        )
    if jurisdiction == "NZ":
        msg = "You appear to provide services captured by the NZ AML/CFT Act 2009. You need an AML/CFT programme."
    else:
        msg = (
            "You appear to provide designated services under the Tranche 2 reforms, which apply from 1 July 2026. "
            "You need to enrol with AUSTRAC and adopt an AML/CTF program."
        )
    return ApplicabilityResult(True, jurisdiction, designated, msg + " This is general information, not legal advice.")
