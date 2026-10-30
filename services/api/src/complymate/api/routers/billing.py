"""Billing: Stripe Checkout and the customer portal. The webhook (webhooks_stripe.py) updates plan and seats."""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, Depends

from complymate.api.deps import Ctx, require
from complymate.db.models import Tenant
from complymate.db.repositories.billing import BillingRepo
from complymate.db.repositories.tenants import TenantRepo
from complymate.domain.audit.events import Action
from complymate.domain.billing.limits import check
from complymate.domain.billing.plans import get_plan
from complymate.domain.errors import ValidationFailed
from complymate.domain.rbac.permissions import P
from complymate.schemas.billing import BillingOut, CheckoutIn, LimitOut, RedirectOut

router = APIRouter(prefix="/billing", tags=["billing"])


async def stripe_client(ctx: Ctx):  # type: ignore[no-untyped-def]
    import stripe

    s = ctx.container.settings
    key = s.stripe_secret_key
    if not key and s.stripe_secret_arn:
        key = (await ctx.container.secrets.get_json(s.stripe_secret_arn))["secret_key"]
    if not key:
        raise ValidationFailed("billing is not configured")
    return stripe.StripeClient(key)


@router.get("", response_model=BillingOut)
async def overview(ctx: Ctx = Depends(require(P.BILLING_READ))) -> BillingOut:
    tenant = await ctx.session.get(Tenant, ctx.tenant_id)
    assert tenant is not None
    plan = get_plan(tenant.plan_code)
    sub = await BillingRepo(ctx.session).subscription(ctx.tenant_id)
    repo = TenantRepo(ctx.session)
    from complymate.domain.billing.usage import period

    usage = await repo.usage(ctx.tenant_id, period())
    seats = await repo.member_count(ctx.tenant_id)
    limits = [check(plan, "users", seats, 0)] + [check(plan, m, usage.get(m, 0), 0) for m in plan.limits]
    return BillingOut(
        plan_code=plan.code,
        plan_name=plan.name,
        price_cents=plan.price_cents,
        status=sub.status if sub else "none",
        seats=seats,
        max_users=plan.max_users,
        trial_ends_at=sub.trial_ends_at if sub else None,
        current_period_end=sub.current_period_end if sub else None,
        onboarding_paid=sub.onboarding_paid if sub else False,
        limits=[
            LimitOut(
                metric=c.metric, used=c.used, limit=c.limit, warning=c.warning, blocked=c.blocked, message=c.message
            )
            for c in limits
        ],
        features=sorted(plan.features),
    )


@router.post("/checkout", response_model=RedirectOut)
async def checkout(body: CheckoutIn, ctx: Ctx = Depends(require(P.BILLING_UPDATE))) -> RedirectOut:
    s = ctx.container.settings
    price = {"solo": s.stripe_price_solo, "practice": s.stripe_price_practice}[body.plan_code]
    if not price:
        raise ValidationFailed("plan price is not configured")
    client = await stripe_client(ctx)
    repo = BillingRepo(ctx.session)
    sub = await repo.subscription(ctx.tenant_id)
    tenant = await ctx.session.get(Tenant, ctx.tenant_id)
    assert tenant is not None and sub is not None
    if not sub.stripe_customer_id:
        customer = await asyncio.to_thread(
            client.customers.create,
            params={"name": tenant.name, "email": ctx.principal.email, "metadata": {"tenant_id": str(tenant.id)}},
        )
        sub.stripe_customer_id = customer.id
    line_items = [{"price": price, "quantity": 1}]
    if body.include_onboarding and s.stripe_price_onboarding and not sub.onboarding_paid:
        line_items.append({"price": s.stripe_price_onboarding, "quantity": 1})
    session = await asyncio.to_thread(
        client.checkout.sessions.create,
        params={
            "mode": "subscription",
            "customer": sub.stripe_customer_id,
            "line_items": line_items,
            "success_url": f"{s.web_base_url}/admin/billing?checkout=success",
            "cancel_url": f"{s.web_base_url}/admin/billing?checkout=cancelled",
            "client_reference_id": str(tenant.id),
            "subscription_data": {"metadata": {"tenant_id": str(tenant.id), "plan_code": body.plan_code}},
            "automatic_tax": {"enabled": True},
        },
    )
    await ctx.record(Action.CREATE, "checkout_session", session.id, after={"plan": body.plan_code})
    return RedirectOut(url=session.url or "")


@router.post("/portal", response_model=RedirectOut)
async def portal(ctx: Ctx = Depends(require(P.BILLING_UPDATE))) -> RedirectOut:
    sub = await BillingRepo(ctx.session).subscription(ctx.tenant_id)
    if not sub or not sub.stripe_customer_id:
        raise ValidationFailed("no billing account yet; choose a plan first")
    client = await stripe_client(ctx)
    session = await asyncio.to_thread(
        client.billing_portal.sessions.create,
        params={
            "customer": sub.stripe_customer_id,
            "return_url": f"{ctx.container.settings.web_base_url}/admin/billing",
        },
    )
    return RedirectOut(url=session.url)
