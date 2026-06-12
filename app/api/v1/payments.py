import asyncio
import logging
import stripe
from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.dependencies import get_current_user
from app.db.session import get_db
from app.schemas.payment import (
    CreateCheckoutSessionRequest,
    CheckoutSessionResponse,
    SessionVerificationResponse,
    PaymentOrderOut,
)
from app.services.payment_service import PaymentService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/payments", tags=["Payments"])

stripe.api_key = settings.STRIPE_SECRET_KEY


@router.post("/create-checkout-session", status_code=201, summary="Create Stripe Checkout Session")
async def create_checkout_session(
    payload: CreateCheckoutSessionRequest,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CheckoutSessionResponse:
    service = PaymentService(db)
    return await service.create_checkout_session(current_user.id, payload)


@router.post("/webhook", include_in_schema=False)
async def stripe_webhook(
    request: Request,
    stripe_signature: str | None = Header(None, alias="stripe-signature"),
    db: AsyncSession = Depends(get_db),
) -> dict:
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
            event = stripe.Event.construct_from(json.loads(raw_body), stripe.api_key)
    except stripe.error.SignatureVerificationError:
        logger.error("Stripe webhook signature verification failed")
        raise HTTPException(status_code=400, detail="Invalid Stripe signature")
    except Exception as exc:
        logger.error("Failed to parse Stripe webhook: %s", exc)
        raise HTTPException(status_code=400, detail="Webhook parse error")

    event_type = event["type"]
    logger.info("Stripe webhook received: %s", event_type)

    if event_type == "checkout.session.completed":
        session_obj = event["data"]["object"]
        service = PaymentService(db)
        try:
            await service.handle_checkout_session_completed(session_obj)
            await db.commit()
        except Exception as exc:
            await db.rollback()
            logger.error("Webhook handler error for session %s: %s", session_obj.get("id"), exc)
            raise HTTPException(status_code=500, detail="Webhook execution failed")

    return {"received": True}


@router.get("/session/{sessionId}", summary="Verify checkout session status")
async def verify_session(
    sessionId: str,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SessionVerificationResponse:
    service = PaymentService(db)
    return await service.verify_session(sessionId, current_user.id)


@router.get("/my-orders", summary="Get my ticket orders")
async def get_my_orders(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    service = PaymentService(db)
    data = await service.get_user_orders(current_user.id)
    return {"orders": data}


@router.get("/my-orders/{orderId}", summary="Get single order detail")
async def get_order_detail(
    orderId: str,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PaymentOrderOut:
    service = PaymentService(db)
    return await service.get_user_order_detail(orderId, current_user.id)

