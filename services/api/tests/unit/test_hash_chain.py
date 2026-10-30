import uuid
from datetime import UTC, datetime

from complymate.domain.audit.hash_chain import GENESIS, compute_hash, verify_chain


def _chain(n: int) -> list[dict]:
    events, prev = [], GENESIS
    for i in range(n):
        e = {
            "id": uuid.uuid4(),
            "tenant_id": uuid.uuid4(),
            "actor_id": None,
            "actor_role": "owner",
            "action": "create",
            "resource_type": "client",
            "resource_id": str(i),
            "before": None,
            "after": {"i": i},
            "reason": None,
            "ip": None,
            "user_agent": None,
            "request_id": None,
            "ai": None,
            "occurred_at": datetime.now(UTC),
        }
        e["prev_hash"] = prev
        e["hash"] = compute_hash(prev, e)
        prev = e["hash"]
        events.append(e)
    return events


def test_valid_chain_verifies():
    result = verify_chain(_chain(5))
    assert result.ok and result.checked == 5


def test_tampered_content_detected():
    events = _chain(4)
    events[2]["after"] = {"i": 999}
    result = verify_chain(events)
    assert not result.ok
    assert result.broken_at_id == str(events[2]["id"])
    assert "content" in result.reason


def test_deleted_row_detected():
    events = _chain(4)
    del events[1]
    result = verify_chain(events)
    assert not result.ok
    assert "prev_hash" in result.reason


def test_hash_is_stable_across_datetime_tz_representation():
    e = _chain(1)[0]
    naive = dict(e, occurred_at=e["occurred_at"].astimezone(UTC).replace(tzinfo=None))
    assert compute_hash(GENESIS, e) == compute_hash(GENESIS, naive)
