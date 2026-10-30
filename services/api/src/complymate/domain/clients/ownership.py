"""Beneficial ownership: effective ownership through layers and the 25% rule, plus a tree for the UI."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

BENEFICIAL_OWNER_THRESHOLD = 25.0


@dataclass
class Party:
    id: UUID
    parent_id: UUID | None
    full_name: str
    is_entity: bool
    ownership_percent: float | None
    party_type: str
    control: bool = False
    is_pep: bool = False
    country: str | None = None


@dataclass
class OwnershipNode:
    party: Party
    effective_percent: float
    depth: int
    children: list[OwnershipNode] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "id": str(self.party.id),
            "name": self.party.full_name,
            "is_entity": self.party.is_entity,
            "party_type": self.party.party_type,
            "direct_percent": self.party.ownership_percent,
            "effective_percent": round(self.effective_percent, 2),
            "depth": self.depth,
            "is_beneficial_owner": is_beneficial_owner(self),
            "is_pep": self.party.is_pep,
            "children": [c.as_dict() for c in self.children],
        }


def is_beneficial_owner(node: OwnershipNode) -> bool:
    if node.party.is_entity:
        return False
    return node.effective_percent >= BENEFICIAL_OWNER_THRESHOLD or node.party.control


def build_tree(parties: list[Party]) -> list[OwnershipNode]:
    by_parent: dict[UUID | None, list[Party]] = {}
    for p in parties:
        by_parent.setdefault(p.parent_id, []).append(p)

    def build(parent: UUID | None, factor: float, depth: int, seen: frozenset[UUID]) -> list[OwnershipNode]:
        nodes = []
        for p in by_parent.get(parent, []):
            if p.id in seen:  # cycle guard
                continue
            direct = (p.ownership_percent or 0.0) / 100.0
            effective = factor * direct * 100.0 if p.ownership_percent is not None else 0.0
            node = OwnershipNode(p, effective, depth)
            node.children = build(
                p.id, factor * direct if p.ownership_percent is not None else 0.0, depth + 1, seen | {p.id}
            )
            nodes.append(node)
        return nodes

    return build(None, 1.0, 1, frozenset())


def flatten(nodes: list[OwnershipNode]) -> list[OwnershipNode]:
    out: list[OwnershipNode] = []
    for n in nodes:
        out.append(n)
        out.extend(flatten(n.children))
    return out


def beneficial_owners(parties: list[Party]) -> list[OwnershipNode]:
    """Natural persons owning ≥25% (directly or indirectly) or with control. Effective % sums through layers."""
    totals: dict[str, OwnershipNode] = {}
    for node in flatten(build_tree(parties)):
        if node.party.is_entity:
            continue
        key = node.party.full_name.casefold()
        if key in totals:
            totals[key].effective_percent += node.effective_percent
        else:
            totals[key] = OwnershipNode(node.party, node.effective_percent, node.depth)
    return [n for n in totals.values() if is_beneficial_owner(n)]


def max_depth(parties: list[Party]) -> int:
    return max((n.depth for n in flatten(build_tree(parties))), default=0)
