import asyncio
import logging

import stripe
from fastapi import APIRouter, Header, HTTPException, Request

from app.core.config import settings
from app.db.session import AsyncSessionLocal
from app.repositories.event_repository import SectionRepository
from app.repositories.order_repository import OrderRepository

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])

stripe.api_key = settings.STRIPE_SECRET_KEY


@router.post("/stripe", include_in_schema=False)
async def stripe_webhook(
    request: Request,
    stripe_signature: str | None = Header(None, alias="stripe-signature"),
) -> dict:
    """
    Receive and verify Stripe webhook events.

    Stripe sends a signed POST to this endpoint. We verify the signature using
    STRIPE_WEBHOOK_SECRET and handle relevant events.
    """
    if not settings.STRIPE_WEBHOOK_SECRET:
        logger.warning("STRIPE_WEBHOOK_SECRET is not set — webhook signature verification skipped")  # noqa: E501

    raw_body = await request.body()

    try:
        if settings.STRIPE_WEBHOOK_SECRET and stripe_signature:
            event = await asyncio.to_thread(
                stripe.Webhook.construct_event,
                raw_body,
                stripe_signature,
                settings.STRIPE_WEBHOOK_SECRET,
            )
        else:
            import json

            event = stripe.Event.construct_from(json.loads(raw_body), stripe.api_key)  # noqa: E501
    except stripe.error.SignatureVerificationError:
        logger.error("Stripe webhook signature verification failed")
        raise HTTPException(status_code=400, detail="Invalid Stripe signature")
    except Exception as exc:
        logger.error("Failed to parse Stripe webhook: %s", exc)
        raise HTTPException(status_code=400, detail="Webhook parse error")

    event_type = event["type"]
    logger.info("Stripe webhook received: %s", event_type)

    if event_type == "payment_intent.succeeded":
        intent = event["data"]["object"]
        await _handle_payment_intent_succeeded(intent)
    elif event_type == "payment_intent.payment_failed":
        intent = event["data"]["object"]
        logger.warning(
            "Payment failed for intent %s: %s",
            intent.get("id"),
            intent.get("last_payment_error", {}).get("message"),
        )

    return {"received": True}


async def _handle_payment_intent_succeeded(intent: dict) -> None:
    intent_id: str = intent.get("id", "")
    if not intent_id:
        return

    async with AsyncSessionLocal() as session:
        try:
            order_repo = OrderRepository(session)
            order = await order_repo.get_by_stripe_intent(intent_id)

            if order and order.status != "completed":
                await order_repo.update_status(order, "completed")

                section_repo = SectionRepository(session)
                section = await section_repo.get_by_id(order.section_id)
                if section:
                    metadata = intent.get("metadata", {})
                    quantity = int(metadata.get("quantity", 1))
                    new_available = max(0, section.available - quantity)
                    await section_repo.update(section, {"available": new_available})  # noqa: E501

                logger.info(
                    "Order %s marked completed via webhook (intent: %s)",
                    order.id,
                    intent_id,
                )

            await session.commit()
        except Exception as exc:
            await session.rollback()
            logger.error("Webhook handler error for intent %s: %s", intent_id, exc)  # noqa: E501
