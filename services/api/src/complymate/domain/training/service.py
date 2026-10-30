"""Training: grading quiz attempts, certificates, overdue checks."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any

from complymate.domain.errors import ValidationFailed


@dataclass
class Grade:
    score: int
    total: int
    percent: float
    passed: bool
    feedback: list[dict[str, Any]]


def grade(questions: list[dict[str, Any]], answers: dict[str, int], pass_mark: int) -> Grade:
    if not questions:
        raise ValidationFailed("module has no approved questions")
    feedback = []
    correct = 0
    for q in questions:
        given = answers.get(str(q["id"]))
        ok = given == q["correct_index"]
        correct += int(ok)
        feedback.append({"question_id": str(q["id"]), "correct": ok, "explanation": q.get("explanation")})
    percent = round(100 * correct / len(questions), 1)
    return Grade(correct, len(questions), percent, percent >= pass_mark, feedback)


def is_overdue(due: date | None, completed: bool, today: date | None = None) -> bool:
    return bool(due) and not completed and due < (today or date.today())  # type: ignore[operator]


def certificate_html(firm: str, user: str, module: str, completed_on: date, percent: float) -> str:
    from html import escape

    return f"""<!doctype html><html><head><meta charset="utf-8"><style>
    @page {{ size: A4 landscape; margin: 2cm; }} body {{ font-family: 'DejaVu Sans', sans-serif; text-align: center; color: #1a1a1a; }}
    .box {{ border: 6px double #0F4C81; padding: 48px; }} h1 {{ color: #0F4C81; font-size: 34pt; margin-bottom: 4px; }}
    .name {{ font-size: 26pt; margin: 24px 0; }} .meta {{ color: #555; }}
    </style></head><body><div class="box"><h1>Certificate of Completion</h1><p class="meta">{escape(firm)}</p>
    <p>This certifies that</p><p class="name">{escape(user)}</p><p>completed the AML/CTF training module</p>
    <h2>{escape(module)}</h2><p class="meta">on {completed_on.isoformat()} with a score of {percent}%</p>
    <p class="meta">Issued by ComplyMate</p></div></body></html>"""
