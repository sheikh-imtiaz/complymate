"""Stripe webhook: verifies the signature, is idempotent (stripe_events), updates plan, status and seats."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

import structlog
from fastapi import APIRouter, Header, Request

from complymate.container import get_container
from complymate.db.models import Subscription, Tenant
from complymate.db.repositories.audit import AuditRepo
from complymate.db.repositories.billing import BillingRepo
from complymate.db.session import apply_context, tenant_session
from complymate.domain.audit.events import Action, AuditContext
from complymate.domain.audit.service import AuditService
from complymate.domain.errors import ValidationFailed

router = APIRouter(tags=["webhooks"])
log = structlog.get_logger(__name__)

STATUS_MAP = {
    "active": "active",
    "trialing": "trialing",
    "past_due": "past_due",
    "canceled": "canceled",
    "unpaid": "past_due",
    "incomplete": "trialing",
    "incomplete_expired": "canceled",
}


async def _secret() -> str:
    c = get_container()
    if c.settings.stripe_webhook_secret:
        return c.settings.stripe_webhook_secret
    if c.settings.stripe_secret_arn:
        return str((await c.secrets.get_json(c.settings.stripe_secret_arn))["webhook_secret"])
    raise ValidationFailed("stripe webhook secret not configured")


@router.post("/webhooks/stripe")
async def stripe_webhook(request: Request, stripe_signature: str = Header(alias="Stripe-Signature")) -> dict[str, str]:
    import stripe

    payload = await request.body()
    try:
        event = stripe.Webhook.construct_event(payload, stripe_signature, await _secret())
    except (ValueError, stripe.SignatureVerificationError) as exc:
        log.warning("security_event", category="stripe_signature_invalid")
        raise ValidationFailed("invalid signature") from exc

    obj: dict[str, Any] = event["data"]["object"]
    async with tenant_session(None, platform=True) as session:
        repo = BillingRepo(session)
        if await repo.event_seen(event["id"], event["type"]):
            return {"status": "duplicate"}
        sub: Subscription | None = None
        if customer := obj.get("customer"):
            sub = await repo.by_customer(customer)
        if sub is None and (tid := (obj.get("metadata") or {}).get("tenant_id") or obj.get("client_reference_id")):
            sub = await repo.subscription(UUID(tid))
        if sub is None:
            log.info("stripe.unmatched_event", type=event["type"])
            return {"status": "ignored"}
        await apply_context(session, sub.tenant_id, platform=True)
        tenant = await session.get(Tenant, sub.tenant_id)
        before = {"plan": sub.plan_code, "status": sub.status}

        if event["type"] == "checkout.session.completed":
            sub.stripe_customer_id = obj.get("customer") or sub.stripe_customer_id
            sub.stripe_subscription_id = obj.get("subscription") or sub.stripe_subscription_id
            sub.onboarding_paid = True
        elif event["type"] in (
            "customer.subscription.created",
            "customer.subscription.updated",
            "customer.subscription.deleted",
        ):
            sub.stripe_subscription_id = obj["id"]
            sub.status = STATUS_MAP.get(obj.get("status", ""), sub.status)
            plan_code = (obj.get("metadata") or {}).get("plan_code")
            if plan_code in ("solo", "practice"):
                sub.plan_code = plan_code
                if tenant:
                    tenant.plan_code = plan_code
            items = (obj.get("items") or {}).get("data") or []
            sub.seats = sum(int(i.get("quantity", 1)) for i in items) or sub.seats
            if obj.get("current_period_end"):
                sub.current_period_end = datetime.fromtimestamp(obj["current_period_end"], UTC)
            if tenant:
                tenant.status = (
                    "active"
                    if sub.status in ("active", "trialing")
                    else ("cancelled" if sub.status == "canceled" else tenant.status)
                )
        elif event["type"] == "invoice.payment_failed":
            sub.status = "past_due"

        await AuditService(AuditRepo(session)).record(
            AuditContext(actor_id=None, actor_role="stripe", tenant_id=sub.tenant_id),
            Action.UPDATE,
            "subscription",
            sub.id,
            before=before,
            after={"plan": sub.plan_code, "status": sub.status, "event": event["type"]},
            tenant_id=sub.tenant_id,
        )
    return {"status": "processed"}
