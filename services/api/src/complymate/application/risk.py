"""Runs the deterministic risk engine for a client and records the result, factors and EDD tasks."""

from __future__ import annotations

from datetime import date, timedelta
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from complymate.db.models import Client, EddTask, RiskAssessment, RiskFactorRow, Tenant
from complymate.db.repositories.clients import ClientRepo
from complymate.domain.clients.ownership import Party, build_tree, flatten
from complymate.domain.risk.engine import edd_tasks_for, next_review_date, score
from complymate.domain.risk.factors import ClientFacts, PartyFacts
from complymate.domain.risk.rules_loader import load_rules


async def build_facts(session: AsyncSession, client: Client) -> ClientFacts:
    repo = ClientRepo(session)
    parties = await repo.parties(client.id)
    tree_nodes = flatten(
        build_tree(
            [
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
                for p in parties
            ]
        )
    )
    depth = {n.party.id: n.depth for n in tree_nodes}
    effective = {n.party.id: n.effective_percent for n in tree_nodes}
    _, open_matches, true_match = await repo.screening_state(client.id)
    return ClientFacts(
        client_type=client.client_type,
        is_pep=client.is_pep,
        nationality=client.nationality,
        residential_country=client.residential_country,
        country_of_incorporation=client.country_of_incorporation,
        services=list(client.services or []),
        channel=client.channel,
        cash_intensive=client.cash_intensive,
        source_of_funds_verified=client.source_of_funds_verified,
        nominee_directors=client.nominee_directors,
        bearer_shares=client.bearer_shares,
        incorporated_on=client.incorporated_on,
        parties=[
            PartyFacts(
                p.is_pep,
                p.country,
                effective.get(p.id, float(p.ownership_percent or 0)),
                p.is_entity,
                depth.get(p.id, 1),
                p.verified,
            )
            for p in parties
        ],
        screening_true_match=true_match,
        screening_open_matches=open_matches,
    )


async def assess(session: AsyncSession, client: Client, actor_id: UUID | None) -> RiskAssessment:
    tenant = await session.get(Tenant, client.tenant_id)
    rules = load_rules(tenant.jurisdiction if tenant else "AU")
    facts = (await build_facts(session, client)).to_facts(rules.home_country)
    result = score(facts, rules)

    previous = await ClientRepo(session).latest_assessment(client.id)
    if previous is not None:
        previous.status = "superseded"
    assessment = RiskAssessment(
        tenant_id=client.tenant_id,
        client_id=client.id,
        rules_version=result.rules_version,
        score=result.score,
        level=result.level,
        reasons=[r.__dict__ for r in result.reasons],
        facts=facts,
        status="approved" if result.level != "high" else "proposed",
        created_by=actor_id,
    )
    session.add(assessment)
    await session.flush()
    for r in result.reasons:
        session.add(
            RiskFactorRow(
                tenant_id=client.tenant_id,
                assessment_id=assessment.id,
                factor_key=r.factor_id,
                category=r.category,
                description=r.description,
                points=r.points,
            )
        )
    existing = {t.key for t in await ClientRepo(session).edd_tasks(client.id) if t.status == "open"}
    for t in edd_tasks_for(result, rules):
        if t["key"] not in existing:
            session.add(
                EddTask(
                    tenant_id=client.tenant_id,
                    client_id=client.id,
                    assessment_id=assessment.id,
                    key=t["key"],
                    title=t["title"],
                    due_date=date.today() + timedelta(days=10),
                )
            )
    client.risk_level = result.level
    client.risk_score = result.score
    if client.status == "approved":
        client.next_review_date = next_review_date(result.level, rules)
    await session.flush()
    return assessment
