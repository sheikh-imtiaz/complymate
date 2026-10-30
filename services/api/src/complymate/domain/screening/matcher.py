"""Fuzzy name matching (rapidfuzz + jellyfish phonetic) with a 0-100 match score."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

import jellyfish
from rapidfuzz import fuzz
from rapidfuzz.distance import JaroWinkler

HONORIFICS = {
    "mr",
    "mrs",
    "ms",
    "miss",
    "dr",
    "prof",
    "sir",
    "dame",
    "hon",
    "the",
    "honourable",
    "general",
    "gen",
    "col",
    "colonel",
    "capt",
    "captain",
    "sheikh",
    "haji",
    "hajji",
    "mullah",
    "maulana",
    "jr",
    "sr",
    "ii",
    "iii",
}
ENTITY_SUFFIXES = {
    "pty",
    "ltd",
    "limited",
    "llc",
    "inc",
    "co",
    "company",
    "corp",
    "corporation",
    "plc",
    "gmbh",
    "sa",
    "ooo",
    "jsc",
    "pjsc",
}

DEFAULT_THRESHOLD = 85.0
STRONG_THRESHOLD = 95.0


def normalize(name: str, *, entity: bool = False) -> str:
    text = unicodedata.normalize("NFKD", name)
    text = "".join(ch for ch in text if not unicodedata.combining(ch)).casefold()
    text = re.sub(r"[^\w\s]", " ", text)
    tokens = [t for t in text.split() if t not in HONORIFICS]
    if entity:
        tokens = [t for t in tokens if t not in ENTITY_SUFFIXES]
    return " ".join(tokens)


def _phonetic_key(name: str) -> set[str]:
    return {jellyfish.metaphone(t) for t in name.split() if len(t) > 1}


@dataclass(frozen=True)
class MatchScore:
    score: float
    method: str
    matched_name: str


def score_names(query: str, candidate: str, *, entity: bool = False) -> MatchScore:
    q = normalize(query, entity=entity)
    c = normalize(candidate, entity=entity)
    if not q or not c:
        return MatchScore(0.0, "empty", candidate)
    if q == c:
        return MatchScore(100.0, "exact", candidate)
    token_set = fuzz.token_set_ratio(q, c)
    token_sort = fuzz.token_sort_ratio(q, c)
    jw = JaroWinkler.normalized_similarity(" ".join(sorted(q.split())), " ".join(sorted(c.split()))) * 100
    best = max(token_sort, jw, token_set * 0.95)  # token_set over-rewards subsets ("John" vs "John Smith")
    method = "fuzzy"
    qk, ck = _phonetic_key(q), _phonetic_key(c)
    if qk and ck:
        overlap = len(qk & ck) / max(len(qk), len(ck))
        if overlap == 1.0 and best < 92:
            best = max(best, 92.0)
            method = "phonetic"
        elif overlap >= 0.5:
            best = min(100.0, best + 3 * overlap)
    # Penalise a single-token query matching only part of a longer name.
    if len(q.split()) == 1 and len(c.split()) > 1:
        best *= 0.85
    return MatchScore(round(best, 1), method, candidate)


def dob_compatible(query_dob: str | None, entry_dob: str | None) -> bool | None:
    """True if compatible, False if clearly different, None if unknown. Entries may list only a year."""
    if not query_dob or not entry_dob:
        return None
    q = re.sub(r"\D", "", query_dob)
    e = re.sub(r"\D", "", entry_dob)
    if len(e) == 4:
        return q.startswith(e) or q.endswith(e)
    return q == e or (q[:4] == e[:4] and q[4:] == e[4:])


def best_match(
    query: str,
    names: list[str],
    *,
    entity: bool = False,
    query_dob: str | None = None,
    entry_dob: str | None = None,
) -> MatchScore:
    best = max(
        (score_names(query, n, entity=entity) for n in names), key=lambda m: m.score, default=MatchScore(0, "none", "")
    )
    compat = dob_compatible(query_dob, entry_dob)
    if compat is True:
        return MatchScore(min(100.0, best.score + 5), best.method + "+dob", best.matched_name)
    if compat is False:
        return MatchScore(round(best.score - 15, 1), best.method + "-dob", best.matched_name)
    return best
