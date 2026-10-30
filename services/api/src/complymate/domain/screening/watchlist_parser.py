"""Parses sanctions lists into WatchlistEntry records.

* DFAT Consolidated List (AU) — CSV export of the XLSX ("Reference", "Name of Individual or Entity", "Type",
  "Name Type", "Date of Birth", "Citizenship", "Committees", ...). Alias rows share the primary's reference.
* NZ list — CSV with "Reference", "Name", "Type", "Aliases" (semicolon separated), "Date of Birth", "Nationality",
  "Regime".
* Sample format (seed/watchlists_sample.csv) uses the NZ-style columns with a "Source" column.
"""

from __future__ import annotations

import csv
import hashlib
import io
import re
from dataclasses import dataclass, field

from complymate.domain.screening.matcher import normalize


@dataclass
class WatchlistEntry:
    source: str
    reference: str
    entity_type: str  # individual | entity
    primary_name: str
    aliases: list[str] = field(default_factory=list)
    dob: str | None = None
    nationality: str | None = None
    program: str | None = None

    @property
    def all_names(self) -> list[str]:
        return [self.primary_name, *self.aliases]

    @property
    def normalized_names(self) -> list[str]:
        entity = self.entity_type == "entity"
        return sorted({normalize(n, entity=entity) for n in self.all_names if n})


def _base_reference(ref: str) -> str:
    # DFAT alias rows look like "123a", "123b"
    return re.sub(r"[a-z]+$", "", ref.strip())


def parse_dfat_csv(content: str) -> list[WatchlistEntry]:
    reader = csv.DictReader(io.StringIO(content))
    entries: dict[str, WatchlistEntry] = {}
    for row in reader:
        ref = _base_reference(row.get("Reference", ""))
        name = (row.get("Name of Individual or Entity") or "").strip()
        if not ref or not name:
            continue
        kind = "individual" if (row.get("Type") or "").lower().startswith("individual") else "entity"
        name_type = (row.get("Name Type") or "").lower()
        if ref not in entries:
            entries[ref] = WatchlistEntry(
                source="DFAT",
                reference=ref,
                entity_type=kind,
                primary_name=name,
                dob=(row.get("Date of Birth") or None),
                nationality=(row.get("Citizenship") or None),
                program=(row.get("Committees") or None),
            )
            if "alias" in name_type:
                entries[ref].aliases.append(name)
        elif "primary" in name_type:
            entries[ref].aliases.append(entries[ref].primary_name)
            entries[ref].primary_name = name
        else:
            entries[ref].aliases.append(name)
    return list(entries.values())


def parse_simple_csv(content: str, default_source: str = "NZ") -> list[WatchlistEntry]:
    reader = csv.DictReader(io.StringIO(content))
    out: list[WatchlistEntry] = []
    for row in reader:
        name = (row.get("Name") or "").strip()
        if not name:
            continue
        out.append(
            WatchlistEntry(
                source=(row.get("Source") or default_source).strip(),
                reference=(row.get("Reference") or "").strip(),
                entity_type="entity" if (row.get("Type") or "").lower().startswith("ent") else "individual",
                primary_name=name,
                aliases=[a.strip() for a in (row.get("Aliases") or "").split(";") if a.strip()],
                dob=(row.get("Date of Birth") or None),
                nationality=(row.get("Nationality") or None),
                program=(row.get("Regime") or None),
            )
        )
    return out


def parse(content: str, source: str) -> list[WatchlistEntry]:
    first_line = content.splitlines()[0] if content else ""
    if "Name of Individual or Entity" in first_line:
        return parse_dfat_csv(content)
    return parse_simple_csv(content, default_source=source)


def checksum(content: str) -> str:
    return hashlib.sha256(content.encode()).hexdigest()
