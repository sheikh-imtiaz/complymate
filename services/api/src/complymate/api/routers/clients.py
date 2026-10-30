from __future__ import annotations

from datetime import UTC, date, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response

from complymate.api.access import load_client
from complymate.api.deps import Ctx, require
from complymate.application.notify import notify
from complymate.application.usage import meter
from complymate.db.models import ClientParty, Tenant, Verification
from complymate.db.repositories.audit import AuditRepo
from complymate.db.repositories.clients import ClientRepo
from complymate.db.repositories.users import UserRepo
from complymate.domain.audit.events import Action
from complymate.domain.clients import service as client_rules
from complymate.domain.clients.ownership import Party, beneficial_owners, build_tree
from complymate.domain.errors import NotFound
from complymate.domain.rbac.permissions import P
from complymate.domain.reports.registers import to_csv, to_xlsx
from complymate.domain.risk.engine import next_review_date
from complymate.domain.risk.rules_loader import load_rules
from complymate.schemas.audit import AuditEventOut
from complymate.schemas.clients import (
    CddChecklistOut,
    ClientCreate,
    ClientListItem,
    ClientOut,
    ClientUpdate,
    PartyIn,
    PartyOut,
    StatusChangeIn,
    VerificationIn,
    VerificationOut,
)
from complymate.schemas.common import Ok, Page

router = APIRouter(prefix="/clients", tags=["clients"])
SENSITIVE = {"date_of_birth", "address", "given_names", "family_name"}


def _safe(data: dict[str, object]) -> dict[str, object]:
    """Audit before/after for clients: keep the business change, not raw identity details."""
    return {k: ("[changed]" if k in SENSITIVE else v) for k, v in data.items()}


@router.get("", response_model=Page[ClientListItem])
async def list_clients(
    q: str | None = None,
    status: str | None = None,
    risk: str | None = None,
    review_overdue: bool = False,
    limit: int = Query(50, le=200),
    offset: int = 0,
    ctx: Ctx = Depends(require(P.CLIENT_READ)),
) -> Page[ClientListItem]:
    rows, total = await ClientRepo(ctx.session).search(
        ctx.scope, ctx.user_id, q=q, status=status, risk=risk, review_overdue=review_overdue, limit=limit, offset=offset
    )
    return Page(items=[ClientListItem.model_validate(r) for r in rows], total=total, limit=limit, offset=offset)


@router.get("/export")
async def export_register(
    format: str = Query("csv", pattern="^(csv|xlsx)$"), ctx: Ctx = Depends(require(P.CLIENT_EXPORT))
) -> Response:
    rows, _ = await ClientRepo(ctx.session).search(ctx.scope, ctx.user_id, limit=100_000)
    cols = [
        "display_name",
        "client_type",
        "status",
        "risk_level",
        "risk_score",
        "next_review_date",
        "last_screened_at",
        "is_pep",
        "residential_country",
        "country_of_incorporation",
        "created_at",
        "approved_at",
    ]
    data = [{c: getattr(r, c) for c in cols} for r in rows]
    await ctx.record(Action.EXPORT, "client_register", None, after={"format": format, "rows": len(data)})
    if format == "xlsx":
        return Response(
            to_xlsx(data, "Client register", cols),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": 'attachment; filename="client-register.xlsx"'},
        )
    return Response(
        to_csv(data, cols),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="client-register.csv"'},
    )


@router.post("", response_model=ClientOut, status_code=201)
async def create_client(body: ClientCreate, ctx: Ctx = Depends(require(P.CLIENT_CREATE))) -> object:
    from complymate.db.models import Client

    await meter(ctx.session, ctx.tenant_id, "clients")
    data = body.model_dump()
    client = Client(
        tenant_id=ctx.tenant_id,
        display_name=client_rules.display_name(body.client_type, body.given_names, body.family_name, body.legal_name),
        created_by=ctx.user_id,
        assigned_to=body.assigned_to or ctx.user_id,
        status="pending",
        **{k: v for k, v in data.items() if k != "assigned_to"},
    )
    ctx.session.add(client)
    await ctx.session.flush()
    await ctx.record(
        Action.CREATE,
        "client",
        client.id,
        after=_safe({"client_type": body.client_type, "display_name": client.display_name}),
    )
    return client


@router.get("/{client_id}", response_model=ClientOut)
async def get_client(client_id: UUID, ctx: Ctx = Depends(require(P.CLIENT_READ))) -> object:
    return await load_client(ctx, client_id)


@router.patch("/{client_id}", response_model=ClientOut)
async def update_client(client_id: UUID, body: ClientUpdate, ctx: Ctx = Depends(require(P.CLIENT_UPDATE))) -> object:
    client = await load_client(ctx, client_id)
    changes = body.model_dump(exclude_unset=True)
    before = {k: getattr(client, k) for k in changes}
    for k, v in changes.items():
        setattr(client, k, v)
    if {"given_names", "family_name", "legal_name"} & set(changes):
        client.display_name = client_rules.display_name(
            client.client_type, client.given_names, client.family_name, client.legal_name
        )
    if changes.get("assigned_to") and changes["assigned_to"] != before.get("assigned_to"):
        await notify(
            ctx.session,
            ctx.container,
            tenant_id=ctx.tenant_id,
            user_ids=[changes["assigned_to"]],
            kind="task_assigned",
            title=f"Client assigned to you: {client.display_name}",
            link=f"/clients/{client.id}",
        )
    await ctx.record(Action.UPDATE, "client", client.id, before=_safe(before), after=_safe(changes))
    return client


@router.delete("/{client_id}", response_model=Ok)
async def delete_client(client_id: UUID, ctx: Ctx = Depends(require(P.CLIENT_DELETE))) -> Ok:
    """AML records must be kept 7 years: only pending clients with no screening can be deleted; others are exited."""
    client = await load_client(ctx, client_id)
    screened, _, _ = await ClientRepo(ctx.session).screening_state(client.id)
    if client.status == "pending" and not screened:
        await ctx.session.delete(client)
        await ctx.record(Action.DELETE, "client", client_id)
        return Ok(message="client deleted")
    client_rules.assert_transition(client.status, "exited")
    client.status = "exited"
    await ctx.record(
        Action.UPDATE, "client", client.id, after={"status": "exited"}, reason="deleted by user; record retained"
    )
    return Ok(message="client exited; records retained for 7 years")


# ---------------- parties / beneficial owners ----------------


@router.get("/{client_id}/parties", response_model=list[PartyOut])
async def list_parties(client_id: UUID, ctx: Ctx = Depends(require(P.CLIENT_READ))) -> list[object]:
    await load_client(ctx, client_id)
    return list(await ClientRepo(ctx.session).parties(client_id))


@router.post("/{client_id}/parties", response_model=PartyOut, status_code=201)
async def add_party(client_id: UUID, body: PartyIn, ctx: Ctx = Depends(require(P.CLIENT_UPDATE))) -> object:
    await load_client(ctx, client_id)
    party = ClientParty(tenant_id=ctx.tenant_id, client_id=client_id, **body.model_dump())
    ctx.session.add(party)
    await ctx.session.flush()
    await ctx.record(
        Action.CREATE,
        "client_party",
        party.id,
        after={
            "client_id": str(client_id),
            "party_type": body.party_type,
            "ownership_percent": str(body.ownership_percent) if body.ownership_percent else None,
        },
    )
    return party


@router.patch("/{client_id}/parties/{party_id}", response_model=PartyOut)
async def update_party(
    client_id: UUID, party_id: UUID, body: PartyIn, ctx: Ctx = Depends(require(P.CLIENT_UPDATE))
) -> object:
    await load_client(ctx, client_id)
    party = await ctx.session.get(ClientParty, party_id)
    if party is None or party.client_id != client_id:
        raise NotFound("party not found")
    for k, v in body.model_dump().items():
        setattr(party, k, v)
    await ctx.record(Action.UPDATE, "client_party", party.id, after={"party_type": body.party_type})
    return party


@router.delete("/{client_id}/parties/{party_id}", response_model=Ok)
async def delete_party(client_id: UUID, party_id: UUID, ctx: Ctx = Depends(require(P.CLIENT_UPDATE))) -> Ok:
    await load_client(ctx, client_id)
    party = await ctx.session.get(ClientParty, party_id)
    if party is None or party.client_id != client_id:
        raise NotFound("party not found")
    await ctx.session.delete(party)
    await ctx.record(Action.DELETE, "client_party", party_id)
    return Ok()


@router.get("/{client_id}/ownership-tree")
async def ownership_tree(client_id: UUID, ctx: Ctx = Depends(require(P.CLIENT_READ))) -> dict[str, object]:
    client = await load_client(ctx, client_id)
    parties = [
        Party(
            p.id,
            p.parent_party_id,
            p.full_name,
            p.is_entity,
            float(p.ownership_percent) if p.ownership_percent is not None else None,
            p.party_type,
            p.has_control,
            p.is_pep,
            p.country,
        )
        for p in await ClientRepo(ctx.session).parties(client_id)
    ]
    return {
        "root": {"name": client.display_name, "client_type": client.client_type},
        "tree": [n.as_dict() for n in build_tree(parties)],
        "beneficial_owners": [
            {
                "name": n.party.full_name,
                "effective_percent": round(n.effective_percent, 2),
                "control": n.party.control,
                "is_pep": n.party.is_pep,
            }
            for n in beneficial_owners(parties)
        ],
    }


# ---------------- CDD checklist / verification ----------------


@router.get("/{client_id}/cdd", response_model=CddChecklistOut)
async def cdd_checklist(client_id: UUID, ctx: Ctx = Depends(require(P.CLIENT_READ))) -> CddChecklistOut:
    client = await load_client(ctx, client_id)
    tenant = await ctx.session.get(Tenant, ctx.tenant_id)
    rules = load_rules(tenant.jurisdiction if tenant else "AU")
    req = rules.cdd["client_types"][client.client_type]
    address = client.address or {}
    present = {
        "given_names": client.given_names,
        "family_name": client.family_name,
        "date_of_birth": client.date_of_birth,
        "residential_address": address.get("line1"),
        "legal_name": client.legal_name,
        "acn": client.acn,
        "nzbn": client.registration_number,
        "registered_address": address.get("registered") or address.get("line1"),
        "principal_place_of_business": address.get("business") or address.get("line1"),
    }
    repo = ClientRepo(ctx.session)
    parties = await repo.parties(client_id)
    party_types = {p.party_type for p in parties}
    present.update(
        {
            "settlor": "settlor" in party_types or None,
            "trustees": "trustee" in party_types or None,
            "partners": "partner" in party_types or None,
            "trust_type": address.get("trust_type"),
        }
    )
    docs = await repo.documents(client_id)
    from sqlalchemy import select

    verifications = (
        (
            await ctx.session.execute(
                select(Verification).where(Verification.client_id == client_id).order_by(Verification.created_at.desc())
            )
        )
        .scalars()
        .all()
    )
    return CddChecklistOut(
        client_type=client.client_type,
        required_fields=req["required_fields"],
        missing_fields=[f for f in req["required_fields"] if not present.get(f)],
        verify_with_one_of=req["verify_with_one_of"],
        documents_present=sorted({d.doc_type for d in docs}),
        checklist=req["checklist"],
        verifications=[VerificationOut.model_validate(v) for v in verifications],
    )


@router.post("/{client_id}/verifications", response_model=VerificationOut, status_code=201)
async def record_verification(
    client_id: UUID, body: VerificationIn, ctx: Ctx = Depends(require(P.CLIENT_UPDATE))
) -> object:
    await load_client(ctx, client_id)
    v = Verification(
        tenant_id=ctx.tenant_id,
        client_id=client_id,
        party_id=body.party_id,
        method=body.method,
        checklist=body.checklist,
        result=body.result,
        verified_by=ctx.user_id,
        verified_at=datetime.now(UTC) if body.result != "pending" else None,
    )
    ctx.session.add(v)
    if body.party_id and body.result == "passed":
        party = await ctx.session.get(ClientParty, body.party_id)
        if party:
            party.verified = True
    await ctx.session.flush()
    await ctx.record(Action.CREATE, "verification", v.id, after={"result": body.result, "method": body.method})
    return v


# ---------------- status ----------------


@router.post("/{client_id}/approve", response_model=ClientOut)
async def approve(client_id: UUID, ctx: Ctx = Depends(require(P.RISK_APPROVE))) -> object:
    client = await load_client(ctx, client_id)
    repo = ClientRepo(ctx.session)
    screened, open_matches, true_match = await repo.screening_state(client.id)
    assessment = await repo.latest_assessment(client.id)
    open_edd = sum(1 for t in await repo.edd_tasks(client.id) if t.status == "open")
    level = (assessment.override_level or assessment.level) if assessment else None
    client_rules.assert_can_approve(
        risk_level=level,
        risk_assessed_by=assessment.created_by if assessment else None,
        created_by=client.created_by,
        approver=ctx.user_id,
        open_matches=open_matches,
        true_match=true_match,
        open_edd_tasks=open_edd,
        screened=screened,
    )
    client_rules.assert_transition(client.status, "approved")
    tenant = await ctx.session.get(Tenant, ctx.tenant_id)
    rules = load_rules(tenant.jurisdiction if tenant else "AU")
    client.status = "approved"
    client.approved_by = ctx.user_id
    client.approved_at = datetime.now(UTC)
    client.next_review_date = next_review_date(level or "medium", rules)
    if assessment and assessment.status == "proposed":
        assessment.status = "approved"
        assessment.approved_by = ctx.user_id
        assessment.approved_at = datetime.now(UTC)
    for task in await ctx.tasks.open_for_resource("client", str(client.id), "approval"):
        task.status, task.completed_at, task.completed_by = "done", datetime.now(UTC), ctx.user_id
    await ctx.record(
        Action.APPROVE,
        "client",
        client.id,
        after={"status": "approved", "risk_level": level, "next_review_date": str(client.next_review_date)},
    )
    return client


@router.post("/{client_id}/request-approval", response_model=Ok)
async def request_approval(client_id: UUID, ctx: Ctx = Depends(require(P.CLIENT_UPDATE))) -> Ok:
    client = await load_client(ctx, client_id)
    approvers = [
        u.id
        for u in await UserRepo(ctx.session).users_with_role(ctx.tenant_id, ("senior_manager", "amlco", "owner"))
        if u.id not in (ctx.user_id, client.created_by)
    ]
    for uid in approvers[:3]:
        await ctx.tasks.create(
            ctx.tenant_id,
            "approval",
            f"Approve client: {client.display_name}",
            assignee_id=uid,
            created_by=ctx.user_id,
            resource_type="client",
            resource_id=str(client.id),
            link=f"/clients/{client.id}",
        )
    await ctx.record(Action.SUBMIT, "client", client.id, after={"approval_requested_from": len(approvers[:3])})
    return Ok(message=f"approval requested from {len(approvers[:3])} people")


@router.post("/{client_id}/decline", response_model=ClientOut)
async def decline(client_id: UUID, body: StatusChangeIn, ctx: Ctx = Depends(require(P.CLIENT_UPDATE))) -> object:
    client = await load_client(ctx, client_id)
    client_rules.assert_transition(client.status, "declined")
    client.status = "declined"
    client.status_reason = body.reason
    await ctx.record(Action.UPDATE, "client", client.id, after={"status": "declined"}, reason=body.reason)
    return client


@router.post("/{client_id}/exit", response_model=ClientOut)
async def exit_client(client_id: UUID, body: StatusChangeIn, ctx: Ctx = Depends(require(P.CLIENT_UPDATE))) -> object:
    client = await load_client(ctx, client_id)
    client_rules.assert_transition(client.status, "exited")
    client.status = "exited"
    client.status_reason = body.reason
    client.next_review_date = None
    await ctx.record(Action.UPDATE, "client", client.id, after={"status": "exited"}, reason=body.reason)
    return client


@router.post("/{client_id}/review-complete", response_model=ClientOut)
async def review_complete(client_id: UUID, ctx: Ctx = Depends(require(P.CLIENT_UPDATE))) -> object:
    """Ongoing CDD: confirms a periodic review and sets the next review date by risk level."""
    client = await load_client(ctx, client_id)
    tenant = await ctx.session.get(Tenant, ctx.tenant_id)
    client.next_review_date = next_review_date(
        client.risk_level or "medium", load_rules(tenant.jurisdiction if tenant else "AU"), date.today()
    )
    for task in await ctx.tasks.open_for_resource("client", str(client.id), "review"):
        task.status, task.completed_at, task.completed_by = "done", datetime.now(UTC), ctx.user_id
    await ctx.record(
        Action.UPDATE,
        "client",
        client.id,
        after={"next_review_date": str(client.next_review_date)},
        reason="ongoing CDD review completed",
    )
    return client


@router.get("/{client_id}/activity", response_model=list[AuditEventOut])
async def activity(client_id: UUID, ctx: Ctx = Depends(require(P.CLIENT_READ))) -> list[object]:
    await load_client(ctx, client_id)
    rows, _ = await AuditRepo(ctx.session).search(
        ctx.tenant_id, resource_type="client", resource_id=str(client_id), limit=200
    )
    return list(rows)
