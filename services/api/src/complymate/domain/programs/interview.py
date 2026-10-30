"""Program Builder guided interview (24 questions) and the program section outline."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Question:
    id: str
    text: str
    kind: str  # text | yesno | choice | multichoice | number
    sections: tuple[str, ...]
    options: tuple[str, ...] = ()
    help: str = ""


@dataclass(frozen=True)
class SectionDef:
    key: str
    title: str
    guidance: str
    rag_query: str
    questions: list[str] = field(default_factory=list)


QUESTIONS: list[Question] = [
    Question(
        "firm_overview",
        "Describe your firm: what you do, where, and roughly how many clients you serve.",
        "text",
        ("purpose_scope", "risk_assessment"),
    ),
    Question(
        "designated_services",
        "Which designated services do you provide?",
        "multichoice",
        ("purpose_scope", "risk_assessment"),
        (
            "real_estate_transaction",
            "handling_client_money",
            "company_or_trust_formation",
            "nominee_director_or_shareholder",
            "registered_office_services",
            "selling_shareholdings_or_businesses",
            "managing_client_accounts",
        ),
    ),
    Question("locations", "Which offices or locations do you provide these services from?", "text", ("purpose_scope",)),
    Question("amlco_name", "Who is the AML/CTF compliance officer and what is their role?", "text", ("governance",)),
    Question(
        "governing_body",
        "Who is the governing body or senior manager responsible for oversight?",
        "text",
        ("governance",),
    ),
    Question(
        "staff_count", "How many staff perform or support designated services?", "number", ("training", "governance")
    ),
    Question(
        "client_types",
        "What types of clients do you have?",
        "multichoice",
        ("risk_assessment", "cdd"),
        ("individual", "company", "trust", "partnership", "foreign"),
    ),
    Question(
        "foreign_clients",
        "Do you act for clients based overseas or with overseas owners? Which countries?",
        "text",
        ("risk_assessment", "risk_methodology"),
    ),
    Question(
        "pep_clients",
        "Do you have, or expect, clients who are politically exposed persons?",
        "yesno",
        ("ecdd", "risk_assessment"),
    ),
    Question("cash_handling", "Do you accept cash? If so, typical amounts?", "text", ("risk_assessment", "reporting")),
    Question(
        "non_face_to_face",
        "Do you onboard clients without meeting them in person?",
        "yesno",
        ("cdd", "risk_methodology"),
    ),
    Question(
        "intermediaries",
        "Do clients come to you through introducers or intermediaries?",
        "yesno",
        ("risk_methodology", "cdd"),
    ),
    Question(
        "high_risk_services",
        "Which of your services do you consider highest risk and why?",
        "text",
        ("risk_assessment",),
    ),
    Question(
        "verification_method",
        "How do you verify identity today (documents sighted, electronic verification)?",
        "text",
        ("cdd",),
    ),
    Question(
        "beneficial_owner_process", "How do you identify beneficial owners of companies and trusts?", "text", ("cdd",)
    ),
    Question("edd_measures", "What extra steps do you take for high-risk clients?", "text", ("ecdd",)),
    Question(
        "ongoing_review",
        "How often do you review existing clients?",
        "choice",
        ("ongoing_cdd",),
        ("annually", "every 2 years", "every 3 years", "on trigger only"),
    ),
    Question("screening_process", "How do you check sanctions and PEP status?", "text", ("screening",)),
    Question(
        "reporting_process", "How do staff raise concerns about suspicious matters internally?", "text", ("reporting",)
    ),
    Question("tipping_off", "How do you make sure staff do not tip off a client?", "text", ("reporting", "training")),
    Question(
        "record_keeping", "Where and how long do you keep client and transaction records?", "text", ("record_keeping",)
    ),
    Question("training_approach", "How will you train staff and how often?", "text", ("training",)),
    Question(
        "employee_due_diligence", "What checks do you run on new staff in AML-relevant roles?", "text", ("training",)
    ),
    Question(
        "independent_review",
        "Who will do the independent evaluation of your program, and how often?",
        "text",
        ("independent_evaluation", "review"),
    ),
]

SECTIONS: list[SectionDef] = [
    SectionDef(
        "purpose_scope",
        "1. Purpose, scope and designated services",
        "State the firm, services covered and how the program applies.",
        "AML/CTF program purpose scope designated services reporting entity",
    ),
    SectionDef(
        "governance",
        "2. Governance and AML/CTF compliance officer",
        "Oversight by the governing body and duties of the AMLCO.",
        "governing body senior manager oversight AML/CTF compliance officer duties",
    ),
    SectionDef(
        "risk_assessment",
        "3. ML/TF risk assessment",
        "Identify and assess money laundering, terrorism financing and proliferation financing risk.",
        "ML/TF risk assessment customer service delivery channel jurisdiction risk",
    ),
    SectionDef(
        "risk_methodology",
        "4. Risk methodology",
        "How customer, service, channel and geography risk combine into a rating.",
        "risk methodology customer risk rating factors low medium high",
    ),
    SectionDef(
        "cdd",
        "5. Customer due diligence",
        "Collect and verify KYC information, including beneficial owners.",
        "customer due diligence identification verification beneficial owner",
    ),
    SectionDef(
        "ecdd",
        "6. Enhanced customer due diligence",
        "When EDD applies (high risk, PEPs, high-risk countries) and the measures.",
        "enhanced customer due diligence politically exposed persons high risk",
    ),
    SectionDef(
        "ongoing_cdd",
        "7. Ongoing customer due diligence",
        "Review cycles and trigger events.",
        "ongoing customer due diligence monitoring review",
    ),
    SectionDef(
        "screening",
        "8. Sanctions and PEP screening",
        "How customers are screened at onboarding and ongoing.",
        "targeted financial sanctions consolidated list screening PEP",
    ),
    SectionDef(
        "reporting",
        "9. Reporting obligations",
        "Suspicious matter reports, threshold transactions, and tipping-off rules.",
        "suspicious matter report tipping off threshold transaction report timeframes",
    ),
    SectionDef(
        "record_keeping",
        "10. Record keeping",
        "What records are kept and for how long (7 years).",
        "record keeping seven years records",
    ),
    SectionDef(
        "training",
        "11. Personnel due diligence and training",
        "Staff screening and risk awareness training.",
        "employee due diligence risk awareness training",
    ),
    SectionDef(
        "independent_evaluation",
        "12. Independent evaluation",
        "Regular independent evaluation of the program.",
        "independent evaluation review AML/CTF program",
    ),
    SectionDef(
        "review",
        "13. Program review and change management",
        "Annual review, change log and approval.",
        "program review update approval governing body",
    ),
]

for _s in SECTIONS:
    _s.questions.extend(q.id for q in QUESTIONS if _s.key in q.sections)

SECTION_KEYS = [s.key for s in SECTIONS]


def section(key: str) -> SectionDef:
    for s in SECTIONS:
        if s.key == key:
            return s
    raise KeyError(key)


def progress(answers: dict[str, object]) -> float:
    answered = sum(1 for q in QUESTIONS if answers.get(q.id) not in (None, "", []))
    return round(answered / len(QUESTIONS), 3)
