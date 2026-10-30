"""Client due diligence flow through the API: create → owners → document/OCR → screen → risk → approve."""

import pytest

pytestmark = pytest.mark.integration


async def test_full_cdd_flow(make_firm, http, headers, seeded_watchlist, container):
    firm = await make_firm("CDD Firm")
    staff = headers(firm.emails["staff"], firm.tenant_id)
    amlco = headers(firm.emails["amlco"], firm.tenant_id)

    resp = await http.post(
        "/clients",
        headers=staff,
        json={
            "client_type": "company",
            "legal_name": "Harbour Holdings Pty Ltd",
            "country_of_incorporation": "AU",
            "services": ["company_or_trust_formation"],
            "channel": "face_to_face",
            "source_of_funds_verified": True,
        },
    )
    assert resp.status_code == 201, resp.text
    client = resp.json()
    cid = client["id"]

    parent = await http.post(
        f"/clients/{cid}/parties",
        headers=staff,
        json={
            "party_type": "shareholder_entity",
            "is_entity": True,
            "full_name": "Holdco Pty Ltd",
            "ownership_percent": 60,
        },
    )
    assert parent.status_code == 201
    await http.post(
        f"/clients/{cid}/parties",
        headers=staff,
        json={
            "parent_party_id": parent.json()["id"],
            "party_type": "beneficial_owner",
            "full_name": "Jane Owner",
            "ownership_percent": 50,
            "verified": True,
        },
    )
    tree = (await http.get(f"/clients/{cid}/ownership-tree", headers=staff)).json()
    assert tree["beneficial_owners"][0]["name"] == "Jane Owner"
    assert tree["beneficial_owners"][0]["effective_percent"] == 30.0

    doc = await http.post(
        f"/clients/{cid}/documents",
        headers=staff,
        data={"doc_type": "asic_extract"},
        files={"file": ("asic.pdf", b"%PDF-1.4 test", "application/pdf")},
    )
    assert doc.status_code == 201, doc.text
    stored = next(v[0] for (_, key), v in container.storage.objects.items() if f"/clients/{cid}/documents/" in key)
    assert stored.startswith(b"CMv1")  # encrypted with the tenant data key

    screen = await http.post(f"/clients/{cid}/screen", headers=staff)
    assert screen.status_code == 201
    assert screen.json()["match_count"] == 0

    risk = await http.post(f"/clients/{cid}/risk", headers=staff)
    assert risk.status_code == 201
    assert risk.json()["level"] in ("low", "medium")

    # Staff cannot approve (needs risk:approve)
    assert (await http.post(f"/clients/{cid}/approve", headers=staff)).status_code == 403
    approved = await http.post(f"/clients/{cid}/approve", headers=amlco)
    assert approved.status_code == 200, approved.text
    assert approved.json()["status"] == "approved"
    assert approved.json()["next_review_date"]


async def test_staff_only_sees_own_clients(make_firm, http, headers):
    firm = await make_firm("Scope Firm")
    owner = headers(firm.emails["owner"], firm.tenant_id)
    staff = headers(firm.emails["staff"], firm.tenant_id)
    await http.post(
        "/clients",
        headers=owner,
        json={
            "client_type": "individual",
            "given_names": "Owner",
            "family_name": "Client",
            "assigned_to": str(firm.users["owner"]),
        },
    )
    mine = await http.post(
        "/clients", headers=staff, json={"client_type": "individual", "given_names": "Staff", "family_name": "Client"}
    )
    listed = (await http.get("/clients", headers=staff)).json()
    assert [c["id"] for c in listed["items"]] == [mine.json()["id"]]


async def test_sanctions_hit_creates_open_match(make_firm, http, headers, seeded_watchlist):
    firm = await make_firm("Match Firm")
    amlco = headers(firm.emails["amlco"], firm.tenant_id)
    c = await http.post(
        "/clients",
        headers=amlco,
        json={
            "client_type": "individual",
            "given_names": "Viktor",
            "family_name": "Ivanoff",
            "date_of_birth": "1961-03-14",
        },
    )
    run = await http.post(f"/clients/{c.json()['id']}/screen", headers=amlco)
    assert run.json()["match_count"] >= 1
    queue = (await http.get("/screening/matches", headers=amlco)).json()
    match = next(m for m in queue if m["client_id"] == c.json()["id"])
    blocked = await http.post(
        f"/clients/{c.json()['id']}/approve", headers=headers(firm.emails["senior_manager"], firm.tenant_id)
    )
    assert blocked.status_code in (409, 422)
    reviewed = await http.post(
        f"/screening/matches/{match['id']}/review",
        headers=amlco,
        json={"decision": "false_positive", "note": "DOB and nationality checked; different person"},
    )
    assert reviewed.json()["status"] == "false_positive"
    # Re-screen keeps the earlier false-positive decision
    again = await http.post(f"/clients/{c.json()['id']}/screen", headers=amlco)
    assert again.json()["match_count"] == 0


async def test_auditor_gets_masked_documents(make_firm, http, headers):
    firm = await make_firm("Mask Firm")
    staff = headers(firm.emails["staff"], firm.tenant_id)
    c = (
        await http.post(
            "/clients", headers=staff, json={"client_type": "individual", "given_names": "A", "family_name": "B"}
        )
    ).json()
    doc = (
        await http.post(
            f"/clients/{c['id']}/documents",
            headers=staff,
            data={"doc_type": "passport"},
            files={"file": ("p.png", b"\x89PNG....", "image/png")},
        )
    ).json()
    await http.post(
        f"/documents/{doc['id']}/confirm",
        headers=staff,
        json={"fields": {"document_number": "PA1234567"}, "apply_to_client": False},
    )
    auditor = headers(firm.emails["auditor"], firm.tenant_id)
    docs = (await http.get(f"/clients/{c['id']}/documents", headers=auditor)).json()
    assert docs[0]["ocr_fields"]["document_number"] != "PA1234567"
    assert (await http.get(f"/documents/{doc['id']}/download", headers=auditor)).status_code == 403
