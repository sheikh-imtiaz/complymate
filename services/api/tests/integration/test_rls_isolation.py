"""Second lock: PostgreSQL RLS isolates tenants even if application code forgets a filter."""

import uuid

import pytest
from sqlalchemy import text

from complymate.db.session import tenant_session

pytestmark = pytest.mark.integration


async def test_app_role_sees_only_its_tenant(make_firm, admin_engine, container):
    a = await make_firm("Firm A")
    b = await make_firm("Firm B")
    async with admin_engine.begin() as conn:
        for firm in (a, b):
            await conn.execute(
                text("INSERT INTO clients (tenant_id, client_type, display_name) VALUES (:t, 'individual', :n)"),
                {"t": firm.tenant_id, "n": f"client-of-{firm.tenant_id}"},
            )

    async with tenant_session(a.tenant_id) as s:
        names = (await s.execute(text("SELECT display_name FROM clients"))).scalars().all()
    assert names and all(n == f"client-of-{a.tenant_id}" for n in names)

    async with tenant_session(None) as s:  # no tenant context → nothing visible
        assert (await s.execute(text("SELECT count(*) FROM clients"))).scalar_one() == 0


async def test_cannot_insert_into_another_tenant(make_firm, container):
    a = await make_firm("Firm C")
    b = await make_firm("Firm D")
    with pytest.raises(Exception, match="row-level security"):
        async with tenant_session(a.tenant_id) as s:
            await s.execute(
                text("INSERT INTO clients (tenant_id, client_type, display_name) VALUES (:t, 'individual', 'x')"),
                {"t": b.tenant_id},
            )


async def test_platform_context_cannot_read_documents_or_smr(make_firm, admin_engine, container):
    firm = await make_firm("Firm E")
    async with admin_engine.begin() as conn:
        cid = (
            await conn.execute(
                text(
                    "INSERT INTO clients (tenant_id, client_type, display_name) VALUES (:t, 'individual', 'p') RETURNING id"
                ),
                {"t": firm.tenant_id},
            )
        ).scalar_one()
        await conn.execute(
            text(
                "INSERT INTO client_documents (tenant_id, client_id, doc_type, storage_key, filename, content_type, size_bytes, sha256) "
                "VALUES (:t, :c, 'passport', 'k', 'f', 'image/png', 1, 'x')"
            ),
            {"t": firm.tenant_id, "c": cid},
        )
        await conn.execute(
            text("INSERT INTO smr_cases (tenant_id, reference, raised_by, summary) VALUES (:t, 'SMR-1', :u, 'secret')"),
            {"t": firm.tenant_id, "u": firm.users["staff"]},
        )
    async with tenant_session(None, platform=True) as s:
        assert (await s.execute(text("SELECT count(*) FROM client_documents"))).scalar_one() == 0
        assert (await s.execute(text("SELECT count(*) FROM smr_cases"))).scalar_one() == 0
        assert (
            await s.execute(text("SELECT count(*) FROM tenants WHERE id = :t"), {"t": firm.tenant_id})
        ).scalar_one() == 1


async def test_api_rejects_foreign_tenant_header(make_firm, http, headers):
    a = await make_firm("Firm F")
    b = await make_firm("Firm G")
    resp = await http.get("/clients", headers=headers(a.emails["owner"], b.tenant_id))
    assert resp.status_code == 403


async def test_api_cannot_read_other_tenants_client_by_id(make_firm, http, headers):
    a = await make_firm("Firm H")
    b = await make_firm("Firm I")
    created = await http.post(
        "/clients",
        headers=headers(b.emails["owner"], b.tenant_id),
        json={"client_type": "individual", "given_names": "Secret", "family_name": "Client"},
    )
    assert created.status_code == 201, created.text
    resp = await http.get(f"/clients/{created.json()['id']}", headers=headers(a.emails["owner"], a.tenant_id))
    assert resp.status_code == 404
    assert uuid.UUID(created.json()["id"])
