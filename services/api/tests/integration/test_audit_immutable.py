"""Audit log is append-only and hash-chained."""

import pytest
from sqlalchemy import text

from complymate.db.repositories.audit import AuditRepo
from complymate.db.session import tenant_session
from complymate.domain.audit.events import AuditContext
from complymate.domain.audit.hash_chain import verify_chain
from complymate.domain.audit.service import AuditService

pytestmark = pytest.mark.integration


async def _write(firm, n=3):
    async with tenant_session(firm.tenant_id) as s:
        svc = AuditService(AuditRepo(s))
        ctx = AuditContext(actor_id=firm.users["owner"], actor_role="owner", tenant_id=firm.tenant_id)
        for i in range(n):
            await svc.record(ctx, "update", "client", str(i), after={"i": i})


async def test_chain_verifies(make_firm, container):
    firm = await make_firm("Audit A")
    await _write(firm, 5)
    async with tenant_session(firm.tenant_id) as s:
        events = [e async for e in AuditRepo(s).iter_chain(firm.tenant_id)]
    result = verify_chain(events)
    assert result.ok and result.checked == 5


async def test_app_role_cannot_update_or_delete(make_firm, container):
    firm = await make_firm("Audit B")
    await _write(firm, 1)
    for stmt in ("UPDATE audit_events SET reason = 'x'", "DELETE FROM audit_events"):
        with pytest.raises(Exception, match="permission denied"):
            async with tenant_session(firm.tenant_id) as s:
                await s.execute(text(stmt))


async def test_owner_role_blocked_by_trigger(make_firm, admin_engine, container):
    firm = await make_firm("Audit C")
    await _write(firm, 1)
    with pytest.raises(Exception, match="append-only"):
        async with admin_engine.begin() as conn:
            await conn.execute(
                text("UPDATE audit_events SET reason = 'tamper' WHERE tenant_id = :t"), {"t": firm.tenant_id}
            )


async def test_api_writes_audit_and_verify_endpoint(make_firm, http, headers):
    firm = await make_firm("Audit D")
    h = headers(firm.emails["owner"], firm.tenant_id)
    await http.patch("/tenants/current", headers=h, json={"size": "11-50"})
    resp = await http.get("/audit", headers=h)
    assert resp.status_code == 200
    assert any(e["resource_type"] == "tenant" for e in resp.json()["items"])
    verify = await http.get("/audit/verify", headers=h)
    assert verify.json()["ok"] is True
