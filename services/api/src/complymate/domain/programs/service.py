"""Program section editing with tracked changes, record locking and version diffs."""

from __future__ import annotations

import difflib
import html
import re
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from complymate.domain.errors import Conflict

LOCK_TTL = timedelta(minutes=5)
_TAG = re.compile(r"<[^>]+>")


def html_to_text(content: str) -> str:
    text = re.sub(r"</(p|h\d|li|div)>", "\n", content or "")
    return html.unescape(_TAG.sub("", text)).strip()


def tracked_change(before_html: str, after_html: str, author: UUID, *, ai: bool = False) -> dict[str, Any]:
    before = html_to_text(before_html).splitlines()
    after = html_to_text(after_html).splitlines()
    diff = list(difflib.unified_diff(before, after, lineterm="", n=1))
    return {
        "at": datetime.now(UTC).isoformat(),
        "author": str(author),
        "ai": ai,
        "added": sum(1 for d in diff if d.startswith("+") and not d.startswith("+++")),
        "removed": sum(1 for d in diff if d.startswith("-") and not d.startswith("---")),
        "diff": diff[:400],
    }


def assert_lock(locked_by: UUID | None, locked_until: datetime | None, user: UUID, now: datetime | None = None) -> None:
    now = now or datetime.now(UTC)
    if locked_by and locked_by != user and locked_until and locked_until > now:
        raise Conflict("section is being edited by someone else")


def new_lock(now: datetime | None = None) -> datetime:
    return (now or datetime.now(UTC)) + LOCK_TTL


def compare_versions(a: list[dict[str, Any]], b: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Section-by-section diff between two versions (lists of {key, title, content_html})."""
    by_key_a = {s["key"]: s for s in a}
    by_key_b = {s["key"]: s for s in b}
    out = []
    for key in list(dict.fromkeys([*by_key_a, *by_key_b])):
        left = html_to_text(by_key_a.get(key, {}).get("content_html", ""))
        right = html_to_text(by_key_b.get(key, {}).get("content_html", ""))
        if left == right:
            out.append(
                {"key": key, "title": (by_key_b.get(key) or by_key_a[key])["title"], "changed": False, "diff": []}
            )
            continue
        diff = list(difflib.ndiff(left.splitlines(), right.splitlines()))
        out.append(
            {
                "key": key,
                "title": (by_key_b.get(key) or by_key_a[key])["title"],
                "changed": True,
                "diff": [d for d in diff if not d.startswith("?")],
            }
        )
    return out
