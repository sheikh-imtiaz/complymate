"""Four-eyes: the person who creates a high-risk decision cannot approve it."""

import pytest

pytestmark = pytest.mark.integration


async def test_high_risk_client_needs_second_person(make_firm, http, headers, seeded_watchlist):
    firm = await make_firm("Four Eyes Firm")
    amlco = headers(firm.emails["amlco"], firm.tenant_id)
    manager = headers(firm.emails["senior_manager"], firm.tenant_id)

    c = (
        await http.post(
            "/clients",
            headers=amlco,
            json={
                "client_type": "individual",
                "given_names": "Pat",
                "family_name": "Example",
                "is_pep": True,
                "residential_country": "AU",
            },
        )
    ).json()
    await http.post(f"/clients/{c['id']}/screen", headers=amlco)
    risk = (await http.post(f"/clients/{c['id']}/risk", headers=amlco)).json()
    assert risk["level"] == "high"

    tasks = (await http.get(f"/clients/{c['id']}/edd-tasks", headers=amlco)).json()
    assert tasks, "high risk creates EDD tasks"
    # EDD must be complete first
    assert (await http.post(f"/clients/{c['id']}/approve", headers=manager)).status_code == 422
    for t in tasks:
        r = await http.patch(
            f"/edd-tasks/{t['id']}", headers=amlco, json={"status": "done", "note": "evidence on file"}
        )
        assert r.status_code == 200

    own = await http.post(f"/clients/{c['id']}/approve", headers=amlco)
    assert own.status_code == 403
    assert own.json()["error"]["code"] == "four_eyes_violation"
    ok = await http.post(f"/clients/{c['id']}/approve", headers=manager)
    assert ok.status_code == 200, ok.text


async def test_program_signoff_four_eyes(make_firm, http, headers):
    firm = await make_firm("Program Firm")
    owner = headers(firm.emails["owner"], firm.tenant_id)
    amlco = headers(firm.emails["amlco"], firm.tenant_id)
    manager = headers(firm.emails["senior_manager"], firm.tenant_id)
    program = (await http.get("/program", headers=owner)).json()
    vid = program["current_version_id"]
    version = (await http.get(f"/program/versions/{vid}", headers=owner)).json()
    for s in version["sections"]:
        r = await http.put(
            f"/program/versions/{vid}/sections/{s['key']}",
            headers=owner,
            json={"content_html": f"<p>{s['title']} text</p>"},
        )
        assert r.status_code == 200, r.text
    assert (await http.post(f"/program/versions/{vid}/submit", headers=owner)).status_code == 200
    assert (
        await http.post(f"/program/versions/{vid}/review", headers=amlco, json={"approve": True})
    ).status_code == 200
    # Owner submitted, so the owner cannot sign off
    own = await http.post(f"/program/versions/{vid}/sign-off", headers=owner, json={"approve": True})
    assert own.status_code == 403
    ok = await http.post(f"/program/versions/{vid}/sign-off", headers=manager, json={"approve": True})
    assert ok.status_code == 200 and ok.json()["locked"] is True
    # Locked versions cannot be edited
    edit = await http.put(
        f"/program/versions/{vid}/sections/governance", headers=owner, json={"content_html": "<p>x</p>"}
    )
    assert edit.status_code == 409
    docx = await http.get(f"/program/versions/{vid}/export?format=docx", headers=owner)
    assert docx.status_code == 200 and docx.content[:2] == b"PK"
