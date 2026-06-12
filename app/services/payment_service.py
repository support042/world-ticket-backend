import asyncio
import logging
import stripe
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import settings
from app.core.exceptions import NotFoundError, ValidationError, ForbiddenError
from app.repositories.event_repository import EventRepository, SectionRepository
from app.repositories.order_repository import OrderRepository
from app.models.order import Order
from app.db.mixins import generate_id
from app.schemas.payment import (
    CreateCheckoutSessionRequest,
    CheckoutSessionResponse,
    SessionVerificationResponse,
    VerificationOrderSchema,
    VerificationSectionSchema,
    PaymentOrderOut,
    PaymentOrderSectionSchema,
    PaymentOrderEventSchema,
    TicketSchema,
)

logger = logging.getLogger(__name__)
stripe.api_key = settings.STRIPE_SECRET_KEY


class PaymentService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.order_repo = OrderRepository(db)
        self.event_repo = EventRepository(db)
        self.section_repo = SectionRepository(db)

    async def create_checkout_session(
        self, user_id: str, payload: CreateCheckoutSessionRequest
    ) -> CheckoutSessionResponse:
        section = await self.section_repo.get_by_id(payload.sectionId)
        if not section:
            raise NotFoundError("Section")

        event = await self.event_repo.get_by_id(section.event_id)
        if not event:
            raise NotFoundError("Event")

        if section.available < payload.quantity:
            raise ValidationError(
                f"Only {section.available} tickets remain for this section"
            )

        # 1. Create Stripe Checkout Session
        session = await asyncio.to_thread(
            stripe.checkout.Session.create,
            success_url=f"{settings.FRONTEND_URL}/payment/success?session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{settings.FRONTEND_URL}/payment/cancel",
            mode="payment",
            customer_email=payload.contactInfo.email,
            line_items=[
                {
                    "price_data": {
                        "currency": section.currency.lower(),
                        "product_data": {
                            "name": f"{event.title} - {section.name}",
                        },
                        "unit_amount": int(round(section.price * 100)),
                    },
                    "quantity": payload.quantity,
                }
            ],
            metadata={
                "section_id": section.id,
                "event_id": event.id,
                "quantity": str(payload.quantity),
                "user_id": user_id,
                "first_name": payload.contactInfo.firstName,
                "last_name": payload.contactInfo.lastName,
                "email": payload.contactInfo.email,
                "phone": payload.contactInfo.phone,
                "gift_option": str(payload.giftOption),
                "team_support": payload.teamSupport or "",
            },
        )

        event_snapshot = {
            "id": event.id,
            "title": event.title,
            "tournament": event.tournament,
            "stage": event.stage,
            "date": event.date,
            "time": event.time,
            "venue": event.venue,
            "city": event.city,
            "country": event.country,
            "image": event.image,
            "teams": event.teams,
        }
        section_snapshot = {
            "id": section.id,
            "name": section.name,
            "row": section.row,
            "price": section.price,
            "currency": section.currency,
        }

        # 2. Save pending Order record
        # Note: We save the Checkout Session ID in stripe_payment_intent_id
        await self.order_repo.create(
            user_id=user_id,
            event_id=event.id,
            section_id=section.id,
            event_snapshot=event_snapshot,
            section_snapshot=section_snapshot,
            quantity=payload.quantity,
            contact_info=payload.contactInfo.model_dump(),
            total_amount=round(section.price * payload.quantity, 2),
            payment_method="card",
            stripe_payment_intent_id=session.id,
            status="pending",
            tickets=[],
            gift_option=payload.giftOption,
            team_support=payload.teamSupport,
        )

        await self.db.commit()

        return CheckoutSessionResponse(
            sessionId=session.id,
            checkoutUrl=session.url,
        )

    async def verify_session(
        self, session_id: str, user_id: str
    ) -> SessionVerificationResponse:
        try:
            session = await asyncio.to_thread(
                stripe.checkout.Session.retrieve,
                session_id,
            )
        except stripe.error.StripeError as exc:
            raise ValidationError(f"Invalid Stripe Session: {exc}") from exc

        # Find the corresponding Order
        order = await self.order_repo.get_by_stripe_intent(session_id)
        if not order:
            raise NotFoundError("Order")

        if order.user_id != user_id:
            raise ForbiddenError("You do not have permission to view this session")

        # Format Order out if exists
        verification_order = None
        if order:
            verification_order = VerificationOrderSchema(
                id=order.id,
                status=order.status,
                quantity=order.quantity,
                totalAmount=order.total_amount,
                section=VerificationSectionSchema(
                    id=order.section_snapshot.get("id", ""),
                    name=order.section_snapshot.get("name", ""),
                    row=order.section_snapshot.get("row", ""),
                    eventTitle=order.event_snapshot.get("title", ""),
                    eventDate=order.event_snapshot.get("date", ""),
                ),
                tickets=[
                    TicketSchema(id=t["id"], barcode=t["barcode"])
                    for t in (order.tickets or [])
                ],
                contactInfo={"email": order.contact_info.get("email", "")},
            )

        return SessionVerificationResponse(
            sessionId=session.id,
            status=session.status,
            amountTotal=session.amount_total or 0,
            currency=session.currency or "usd",
            order=verification_order,
        )

    async def get_user_orders(self, user_id: str) -> list[PaymentOrderOut]:
        # Retrieve all orders for the user from DB
        stmt = (
            select(Order)
            .where(Order.user_id == user_id)
            .order_by(Order.created_at.desc())
        )
        result = await self.db.execute(stmt)
        orders = result.scalars().all()

        out_orders = []
        for o in orders:
            # Return same shape as requested
            out_orders.append(
                PaymentOrderOut(
                    id=o.id,
                    stripeSessionId=o.stripe_payment_intent_id,
                    status=o.status,
                    quantity=o.quantity,
                    totalAmount=o.total_amount,
                    createdAt=o.created_at,
                    section=PaymentOrderSectionSchema(
                        id=o.section_snapshot.get("id", ""),
                        name=o.section_snapshot.get("name", ""),
                        row=o.section_snapshot.get("row", ""),
                    ),
                    event=PaymentOrderEventSchema(
                        id=o.event_snapshot.get("id", ""),
                        title=o.event_snapshot.get("title", ""),
                        date=o.event_snapshot.get("date", ""),
                        venue=o.event_snapshot.get("venue", ""),
                        city=o.event_snapshot.get("city", ""),
                    ),
                    tickets=[
                        TicketSchema(id=t["id"], barcode=t["barcode"])
                        for t in (o.tickets or [])
                    ],
                )
            )
        return out_orders

    async def get_user_order_detail(
        self, order_id: str, user_id: str
    ) -> PaymentOrderOut:
        order = await self.order_repo.get_by_id(order_id)
        if not order:
            raise NotFoundError("Order")

        if order.user_id != user_id:
            raise ForbiddenError("You do not have permission to view this order")

        return PaymentOrderOut(
            id=order.id,
            stripeSessionId=order.stripe_payment_intent_id,
            status=order.status,
            quantity=order.quantity,
            totalAmount=order.total_amount,
            createdAt=order.created_at,
            section=PaymentOrderSectionSchema(
                id=order.section_snapshot.get("id", ""),
                name=order.section_snapshot.get("name", ""),
                row=order.section_snapshot.get("row", ""),
            ),
            event=PaymentOrderEventSchema(
                id=order.event_snapshot.get("id", ""),
                title=order.event_snapshot.get("title", ""),
                date=order.event_snapshot.get("date", ""),
                venue=order.event_snapshot.get("venue", ""),
                city=order.event_snapshot.get("city", ""),
            ),
            tickets=[
                TicketSchema(id=t["id"], barcode=t["barcode"])
                for t in (order.tickets or [])
            ],
        )

    async def handle_checkout_session_completed(
        self, session: stripe.checkout.Session
    ) -> None:
        session_id = session.id
        # Find order by session id (stripe_payment_intent_id)
        order = await self.order_repo.get_by_stripe_intent(session_id)
        if not order:
            logger.warning(
                f"Order not found for completed Stripe Session {session_id}"
            )
            return

        if order.status == "paid":
            # Already processed
            return

        # Generate ticket records
        tickets = []
        for i in range(order.quantity):
            ticket_id = generate_id("tkt")
            barcode = f"QR_{order.id}_{i+1}"
            tickets.append({"id": ticket_id, "barcode": barcode})

        # Update order status & tickets
        order.tickets = tickets
        order.status = "paid"

        # Decrement available tickets in Section
        section = await self.section_repo.get_by_id(order.section_id)
        if section:
            new_available = max(0, section.available - order.quantity)
            await self.section_repo.update(section, {"available": new_available})

        logger.info(
            f"Order {order.id} marked as paid via webhook (Session: {session_id}). Generated {order.quantity} tickets."
        )
