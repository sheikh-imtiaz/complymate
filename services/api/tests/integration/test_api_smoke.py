"""Broad API smoke tests across routers (sign-up, chat, SMR, training, reports, platform admin)."""

import uuid

import pytest
from sqlalchemy import text

pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
async def kb(container):
    from complymate.workers.seed_reference import seed_kb, seed_training

    await seed_kb()
    await seed_training()


async def test_signup_creates_firm_and_owner(http, headers):
    email = f"founder.{uuid.uuid4().hex[:6]}@test.example"
    me = (await http.get("/auth/me", headers=headers(email))).json()
    assert me["tenant_id"] is None and me["memberships"] == []
    resp = await http.post(
        "/tenants",
        headers=headers(email),
        json={
            "name": "New Firm Pty Ltd",
            "jurisdiction": "AU",
            "abn": "51 824 753 556",
            "services": ["real_estate_transaction"],
            "plan_code": "solo",
        },
    )
    assert resp.status_code == 201, resp.text
    firm = resp.json()
    assert firm["tranche2_applies"] is True
    me = (await http.get("/auth/me", headers=headers(email, firm["id"]))).json()
    assert me["role_key"] == "owner" and "billing:update" in me["permissions"]
    bad = await http.post("/tenants", headers=headers(email), json={"name": "X Pty", "abn": "12345678901"})
    assert bad.status_code == 422


async def test_invitation_flow(make_firm, http, headers):
    firm = await make_firm("Invite Firm")
    owner = headers(firm.emails["owner"], firm.tenant_id)
    invitee = f"new.{uuid.uuid4().hex[:6]}@test.example"
    inv = await http.post("/invitations", headers=owner, json={"email": invitee, "role_key": "staff"})
    assert inv.status_code == 201, inv.text
    token = inv.json()["accept_url"].split("token=")[1]
    wrong = await http.post(
        "/invitations/accept", headers=headers(f"other.{uuid.uuid4().hex[:4]}@test.example"), json={"token": token}
    )
    assert wrong.status_code == 403
    ok = await http.post("/invitations/accept", headers=headers(invitee), json={"token": token})
    assert ok.status_code == 200, ok.text
    me = (await http.get("/auth/me", headers=headers(invitee, firm.tenant_id))).json()
    assert me["role_key"] == "staff"


async def test_chat_answers_with_citations_and_blocks_tipping_off(make_firm, http, headers, kb):
    firm = await make_firm("Chat Firm")
    staff = headers(firm.emails["staff"], firm.tenant_id)
    resp = await http.post(
        "/chat",
        headers=staff,
        json={"message": "How quickly must we lodge a suspicious matter report?", "stream": False},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["citations"], "answers must show sources"
    assert body["citations"][0]["last_checked_at"]
    assert "not legal advice" in body["answer"].lower()
    blocked = await http.post(
        "/chat",
        headers=staff,
        json={"message": "Should I tell the client we reported them to AUSTRAC?", "stream": False},
    )
    assert "tipping-off" in blocked.json()["answer"].lower()
    fb = await http.post(
        f"/chat/messages/{body['message_id']}/feedback", headers=staff, json={"rating": "wrong", "comment": "x"}
    )
    assert fb.status_code == 200
    sse = await http.post("/chat", headers=staff, json={"message": "What is a beneficial owner?"})
    assert sse.headers["content-type"].startswith("text/event-stream")
    assert "event: done" in sse.text


async def test_smr_strict_access_and_export(make_firm, http, headers):
    firm = await make_firm("SMR Firm")
    staff = headers(firm.emails["staff"], firm.tenant_id)
    amlco = headers(firm.emails["amlco"], firm.tenant_id)
    auditor = headers(firm.emails["auditor"], firm.tenant_id)
    case = await http.post("/smr", headers=staff, json={"summary": "Client paid deposit in many small cash amounts."})
    assert case.status_code == 201
    cid = case.json()["id"]
    assert (await http.post(f"/smr/{cid}/submit", headers=staff)).status_code == 200
    assert (await http.patch(f"/smr/{cid}", headers=staff, json={"grounds": "x"})).status_code == 403
    detail = (await http.get(f"/smr/{cid}", headers=amlco)).json()
    assert "Tipping-off" in detail["tipping_off_warning"]
    assert (await http.post(f"/smr/{cid}/ai-assist", headers=amlco)).json()["ai_suggestion"]
    await http.patch(
        f"/smr/{cid}",
        headers=amlco,
        json={"grounds": "Structuring below threshold", "suspicion_categories": ["structuring"]},
    )
    decided = await http.post(
        f"/smr/{cid}/decide", headers=amlco, json={"report": True, "reason": "Pattern consistent with structuring"}
    )
    assert decided.status_code == 200, decided.text
    export = await http.get(f"/smr/{cid}/export", headers=amlco)
    assert export.status_code == 200 and export.content[:2] == b"PK"
    # Auditor can read but not export
    assert (await http.get(f"/smr/{cid}/export", headers=auditor)).status_code == 403


async def test_training_attempt_and_certificate(make_firm, http, headers, kb):
    firm = await make_firm("Training Firm")
    staff = headers(firm.emails["staff"], firm.tenant_id)
    modules = (await http.get("/training/modules", headers=staff)).json()
    module = next(m for m in modules if m["title"].startswith("AML/CTF basics"))
    detail = (await http.get(f"/training/modules/{module['id']}", headers=staff)).json()
    answers = {q["id"]: 0 for q in detail["questions"]}
    answers[detail["questions"][1]["id"]] = 1
    answers[detail["questions"][2]["id"]] = 2
    result = await http.post(f"/training/modules/{module['id']}/attempts", headers=staff, json={"answers": answers})
    assert result.status_code == 201, result.text
    assert result.json()["attempt"]["passed"] is True
    cert = await http.get(f"/training/certificates/{result.json()['attempt']['id']}", headers=staff)
    assert cert.status_code == 200 and cert.content[:4] == b"%PDF"


async def test_reports_dashboard_and_regulator_pack(make_firm, http, headers, container):
    firm = await make_firm("Report Firm")
    owner = headers(firm.emails["owner"], firm.tenant_id)
    await http.post(
        "/clients", headers=owner, json={"client_type": "individual", "given_names": "R", "family_name": "C"}
    )
    dash = (await http.get("/reports/dashboard", headers=owner)).json()
    assert dash["clients_by_risk"]["unassessed"] == 1
    csv = await http.get("/reports/client-register?format=csv", headers=owner)
    assert csv.status_code == 200 and b"display_name" in csv.content
    job = (await http.post("/reports/regulator-pack", headers=owner)).json()
    from complymate.workers.build_regulator_pack import run

    result = await run({"tenant_id": str(firm.tenant_id), "job_id": job["id"]})
    assert result["status"] == "done"
    dl = await http.get(f"/exports/{result['export_id']}/download", headers=owner)
    assert dl.json()["url"].startswith("memory://")


async def test_platform_admin(admin_engine, http, headers, make_firm, token):
    firm = await make_firm("Platform Target")
    email = f"admin.{uuid.uuid4().hex[:6]}@complymate.test"
    async with admin_engine.begin() as conn:
        await conn.execute(
            text(
                "INSERT INTO users (external_sub, email, platform_role, mfa_enrolled) VALUES (:s, :e, 'super_admin', true)"
            ),
            {"s": f"dev-{uuid.uuid5(uuid.NAMESPACE_URL, email)}", "e": email},
        )
    admin = headers(email)
    tenants = (await http.get("/platform/tenants", headers=admin)).json()
    assert any(t["id"] == str(firm.tenant_id) for t in tenants)
    assert (
        await http.put(
            "/platform/feature-flags",
            headers=admin,
            json={"key": "xero_integration", "enabled": True, "tenant_id": str(firm.tenant_id)},
        )
    ).status_code == 200
    flags = (await http.get("/tenants/current/flags", headers=headers(firm.emails["owner"], firm.tenant_id))).json()
    assert flags["xero_integration"] is True
    assert (
        await http.post(
            f"/platform/tenants/{firm.tenant_id}/suspend", headers=admin, json={"reason": "non-payment test"}
        )
    ).status_code == 200
    assert (await http.get("/clients", headers=headers(firm.emails["owner"], firm.tenant_id))).status_code == 403
    await http.post(f"/platform/tenants/{firm.tenant_id}/reactivate", headers=admin, json={"reason": "paid"})
    health = (await http.get("/platform/system-health", headers=admin)).json()
    assert health["database"] == "ok"
    usage = (await http.get("/platform/usage-costs", headers=admin)).json()
    assert "total_usd" in usage
    # Tenant users cannot call platform endpoints
    assert (
        await http.get("/platform/tenants", headers=headers(firm.emails["owner"], firm.tenant_id))
    ).status_code == 403


async def test_impersonation_requires_consent(admin_engine, http, headers, make_firm):
    firm = await make_firm("Consent Firm")
    email = f"support.{uuid.uuid4().hex[:6]}@complymate.test"
    async with admin_engine.begin() as conn:
        await conn.execute(
            text("INSERT INTO users (external_sub, email, platform_role) VALUES (:s, :e, 'platform_support')"),
            {"s": f"dev-{uuid.uuid5(uuid.NAMESPACE_URL, email)}", "e": email},
        )
    support = headers(email)
    imp = await http.post(
        "/platform/impersonation",
        headers=support,
        json={"tenant_id": str(firm.tenant_id), "reason": "Customer asked for help with screening", "minutes": 15},
    )
    assert imp.status_code == 201, imp.text
    imp_id = imp.json()["id"]
    as_support = {**support, "X-Impersonation-Id": imp_id}
    assert (await http.get("/clients", headers=as_support)).status_code == 403  # no consent yet
    owner = headers(firm.emails["owner"], firm.tenant_id)
    assert (
        await http.post(
            f"/tenants/current/impersonation-requests/{imp_id}/consent", headers=owner, json={"approve": True}
        )
    ).status_code == 200
    assert (await http.get("/clients", headers=as_support)).status_code == 200
    assert (
        await http.post(
            "/clients", headers=as_support, json={"client_type": "individual", "given_names": "x", "family_name": "y"}
        )
    ).status_code == 403
