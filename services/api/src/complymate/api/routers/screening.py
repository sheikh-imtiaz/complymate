from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends
from fastapi.responses import Response
from jinja2 import Environment, FileSystemLoader, select_autoescape

from complymate.api.access import load_client
from complymate.api.deps import Ctx, require
from complymate.application.notify import notify
from complymate.application.screening import screen_client
from complymate.db.models import ScreeningMatch, Tenant
from complymate.db.repositories.screening import ScreeningRepo
from complymate.db.repositories.users import UserRepo
from complymate.domain.audit.events import Action
from complymate.domain.errors import Forbidden, NotFound
from complymate.domain.programs.export import html_to_pdf
from complymate.domain.rbac.permissions import P
from complymate.domain.rbac.policy import scope_for
from complymate.schemas.screening import (
    MatchReviewIn,
    PepDeclarationIn,
    RunOut,
    ScreeningOut,
    WatchlistVersionOut,
)

router = APIRouter(tags=["screening"])


@router.post("/clients/{client_id}/screen", response_model=RunOut, status_code=201)
async def screen(client_id: UUID, ctx: Ctx = Depends(require(P.SCREENING_CREATE))) -> object:
    ctx.scope = scope_for(ctx.principal, P.CLIENT_READ) or ctx.scope
    client = await load_client(ctx, client_id)
    run, matches = await screen_client(ctx.session, client, trigger="manual", actor_id=ctx.user_id)
    if matches:
        reviewers = [u.id for u in await UserRepo(ctx.session).users_with_role(ctx.tenant_id, ("amlco",))]
        await notify(
            ctx.session,
            ctx.container,
            tenant_id=ctx.tenant_id,
            user_ids=reviewers,
            kind="screening_match",
            title=f"{len(matches)} possible match(es) for {client.display_name}",
            link="/screening",
        )
        for uid in reviewers:
            await ctx.tasks.create(
                ctx.tenant_id,
                "rescreen_match",
                f"Review screening matches: {client.display_name}",
                assignee_id=uid,
                created_by=ctx.user_id,
                resource_type="client",
                resource_id=str(client.id),
                link="/screening",
            )
    await ctx.record(Action.SCREEN, "client", client.id, after={"run_id": str(run.id), "matches": len(matches)})
    return run


@router.get("/clients/{client_id}/screening", response_model=ScreeningOut)
async def client_screening(client_id: UUID, ctx: Ctx = Depends(require(P.SCREENING_READ))) -> ScreeningOut:
    await load_client(ctx, client_id) if scope_for(ctx.principal, P.CLIENT_READ) else None
    repo = ScreeningRepo(ctx.session)
    return ScreeningOut(
        runs=[RunOut.model_validate(r) for r in await repo.runs(client_id)],
        matches=await repo.matches(client_id=client_id),
    )


@router.get("/screening/matches")
async def review_queue(status: str = "open", ctx: Ctx = Depends(require(P.SCREENING_READ))) -> list[dict[str, object]]:
    return await ScreeningRepo(ctx.session).matches(status=status)


@router.post("/screening/matches/{match_id}/review")
async def review_match(
    match_id: UUID, body: MatchReviewIn, ctx: Ctx = Depends(require(P.SCREENING_UPDATE))
) -> dict[str, object]:
    match = await ctx.session.get(ScreeningMatch, match_id)
    if match is None:
        raise NotFound("match not found")
    if body.decision == "true_match" and scope_for(ctx.principal, P.SCREENING_APPROVE) is None:
        raise Forbidden("only the compliance officer can confirm a true match")
    before = {"status": match.status}
    match.status = body.decision
    match.review_note = body.note
    match.reviewed_by = ctx.user_id
    match.reviewed_at = datetime.now(UTC)
    from complymate.db.models import Client

    client = await ctx.session.get(Client, match.client_id)
    if body.decision == "true_match" and client is not None:
        client.risk_level = "high"
        await ctx.tasks.create(
            ctx.tenant_id,
            "smr",
            f"Confirmed sanctions match: decline {client.display_name} and consider an SMR",
            assignee_id=ctx.user_id,
            created_by=ctx.user_id,
            resource_type="client",
            resource_id=str(client.id),
            link=f"/clients/{client.id}",
        )
    await ctx.record(
        Action.DECIDE, "screening_match", match.id, before=before, after={"status": body.decision}, reason=body.note
    )
    return {"id": str(match.id), "status": match.status}


@router.post("/clients/{client_id}/pep-declaration")
async def pep_declaration(
    client_id: UUID, body: PepDeclarationIn, ctx: Ctx = Depends(require(P.CLIENT_UPDATE))
) -> dict[str, bool]:
    """PEP screening starts with a manual declaration; a provider integration can be added later."""
    client = await load_client(ctx, client_id)
    before = {"is_pep": client.is_pep}
    client.is_pep = body.is_pep
    client.pep_details = body.details
    await ctx.record(
        Action.UPDATE, "client", client.id, before=before, after={"is_pep": body.is_pep}, reason="PEP declaration"
    )
    return {"is_pep": client.is_pep}


@router.get("/screening/watchlists", response_model=list[WatchlistVersionOut])
async def watchlists(ctx: Ctx = Depends(require(P.SCREENING_READ))) -> list[object]:
    return list(await ScreeningRepo(ctx.session).current_versions())


@router.get("/clients/{client_id}/screening/certificate")
async def certificate(client_id: UUID, ctx: Ctx = Depends(require(P.SCREENING_READ))) -> Response:
    client = await load_client(ctx, client_id) if scope_for(ctx.principal, P.CLIENT_READ) else None
    if client is None:
        raise Forbidden("client not accessible")
    repo = ScreeningRepo(ctx.session)
    runs = await repo.runs(client_id)
    if not runs:
        raise NotFound("client has not been screened")
    tenant = await ctx.session.get(Tenant, ctx.tenant_id)
    env = Environment(loader=FileSystemLoader(ctx.container.settings.templates_dir), autoescape=select_autoescape())
    html = env.get_template("screening_certificate.html").render(
        firm=tenant.name if tenant else "",
        client=client,
        run=runs[0],
        versions=await repo.current_versions(),
        matches=await repo.matches(client_id=client_id),
        generated_at=datetime.now(UTC),
    )
    pdf = await asyncio.to_thread(html_to_pdf, html)
    await ctx.record(Action.EXPORT, "screening_certificate", client.id)
    return Response(
        pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="screening-certificate-{client.id}.pdf"'},
    )
