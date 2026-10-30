"""Guardrails around every agent call (in addition to Bedrock Guardrails / Azure AI Content Safety):

* input: tipping-off requests, prompt-injection markers, out-of-scope requests
* output: citations required, no invented source markers, disclaimer on legal content, no ID numbers
* logs: PII masked (observability.pii_filter)
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

DISCLAIMER = "General information, not legal advice. Check with your AML/CTF compliance officer for your situation."

_TIPPING_OFF = re.compile(
    r"\b(tell|inform|warn|let .{0,20}know|notify|email|message|text)\b.{0,60}\b(client|customer|him|her|them)\b"
    r".{0,80}\b(smr|suspicious matter|report(ed)? (to|them to) austrac|investigat|austrac|reported)\b",
    re.I | re.S,
)
_DRAFT_TIPOFF = re.compile(
    r"\b(draft|write)\b.{0,40}\b(letter|email|message)\b.{0,60}\b(smr|suspicious|austrac report)\b", re.I | re.S
)
_INJECTION = re.compile(
    r"(ignore (all|any|the|previous|prior) (instructions|rules)|system prompt|you are now|developer mode|"
    r"reveal your (instructions|prompt)|jailbreak)",
    re.I,
)
_ID_NUMBER = re.compile(r"\b([A-Z]{1,2}\d{6,9}|\d{9,11})\b")
_CITATION = re.compile(r"\[S(\d+)\]")


@dataclass
class InputCheck:
    allowed: bool
    category: str | None = None
    message: str | None = None
    flags: list[str] = field(default_factory=list)


@dataclass
class OutputCheck:
    text: str
    flags: list[str] = field(default_factory=list)
    cited: list[int] = field(default_factory=list)


TIPPING_OFF_REPLY = (
    "I can't help with telling a customer (or anyone outside your compliance team) about a suspicious matter report "
    "or a possible report. Doing so may be the tipping-off offence under the AML/CTF Act (AU) or AML/CFT Act (NZ). "
    "If you are unsure what you can say to the customer, speak to your AML/CTF compliance officer."
)


def check_input(text: str) -> InputCheck:
    flags = []
    if _INJECTION.search(text):
        flags.append("prompt_injection_marker")
    if _TIPPING_OFF.search(text) or _DRAFT_TIPOFF.search(text):
        return InputCheck(False, "tipping_off", TIPPING_OFF_REPLY, flags + ["tipping_off"])
    if len(text) > 4000:
        return InputCheck(False, "too_long", "Please shorten your question to under 4,000 characters.", flags)
    return InputCheck(True, flags=flags)


def check_output(text: str, source_count: int) -> OutputCheck:
    flags: list[str] = []
    cited = sorted({int(n) for n in _CITATION.findall(text)})
    invalid = [n for n in cited if n < 1 or n > source_count]
    if invalid:
        flags.append("invalid_citation")
        text = _CITATION.sub(lambda m: m.group(0) if 1 <= int(m.group(1)) <= source_count else "", text)
        cited = [n for n in cited if n not in invalid]
    if source_count and not cited:
        flags.append("uncited_answer")
    if _ID_NUMBER.search(text):
        flags.append("id_number_redacted")
        text = _ID_NUMBER.sub("[redacted]", text)
    if _TIPPING_OFF.search(text) and "tipping-off" not in text.lower():
        flags.append("tipping_off_output_blocked")
        text = TIPPING_OFF_REPLY
    if DISCLAIMER not in text and "not legal advice" not in text.lower():
        text = f"{text.rstrip()}\n\n_{DISCLAIMER}_"
    return OutputCheck(text, flags, cited)


def sanitize_html(html: str) -> str:
    """Program drafts: allow a small tag set only."""
    html = re.sub(r"<\s*(script|style|iframe|object|embed)[^>]*>.*?<\s*/\s*\1\s*>", "", html, flags=re.I | re.S)
    html = re.sub(r"\son\w+\s*=\s*(\"[^\"]*\"|'[^']*'|[^\s>]+)", "", html, flags=re.I)
    html = re.sub(r"javascript:", "", html, flags=re.I)
    allowed = {"h2", "h3", "h4", "p", "ul", "ol", "li", "strong", "em", "b", "i", "br", "blockquote"}
    return re.sub(
        r"</?([a-zA-Z0-9]+)[^>]*>",
        lambda m: m.group(0) if m.group(1).lower() in allowed else "",
        html,
    )
