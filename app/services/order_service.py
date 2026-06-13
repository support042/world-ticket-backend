import asyncio

import stripe
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import ForbiddenError, NotFoundError, ValidationError
from app.repositories.event_repository import (
    EventRepository,
    SectionRepository,
)
from app.repositories.order_repository import OrderRepository
from app.schemas.order import CreateOrderRequest, OrderListParams, OrderOut


class OrderService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.order_repo = OrderRepository(db)
        self.event_repo = EventRepository(db)
        self.section_repo = SectionRepository(db)

    async def create_order(
        self,
        payload: CreateOrderRequest,
        user_id: str | None,
    ) -> OrderOut:
        stripe.api_key = settings.STRIPE_SECRET_KEY
        try:
            pi = await asyncio.to_thread(
                stripe.PaymentIntent.retrieve,
                payload.stripePaymentIntentId,
            )
        except stripe.error.StripeError as exc:
            raise ValidationError(f"Invalid payment intent: {exc}") from exc

        if pi.status != "succeeded":
            raise ValidationError(f"Payment has not been completed (status: {pi.status})")  # noqa: E501

        event = await self.event_repo.get_by_id(payload.eventId)
        if not event:
            raise NotFoundError("Event")

        section = await self.section_repo.get_by_id(payload.sectionId)
        if not section or section.event_id != payload.eventId:
            raise NotFoundError("Section")

        if section.available < payload.quantity:
            raise ValidationError(
                f"Only {section.available} tickets remain for this section",
            )

        existing = await self.order_repo.get_by_stripe_intent(
            payload.stripePaymentIntentId,
        )
        if existing:
            return OrderOut.from_orm_model(existing)

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

        from sqlalchemy.exc import IntegrityError

        try:
            order = await self.order_repo.create(
                user_id=user_id,
                event_id=event.id,
                section_id=section.id,
                event_snapshot=event_snapshot,
                section_snapshot=section_snapshot,
                quantity=payload.quantity,
                contact_info=payload.contactInfo.model_dump(),
                total_amount=payload.totalAmount,
                payment_method=payload.paymentMethod,
                stripe_payment_intent_id=payload.stripePaymentIntentId,
                status="completed",
            )
            new_available = max(0, section.available - payload.quantity)
            await self.section_repo.update(section, {"available": new_available})
            return OrderOut.from_orm_model(order)
        except IntegrityError:
            await self.db.rollback()
            existing = await self.order_repo.get_by_stripe_intent(
                payload.stripePaymentIntentId,
            )
            if existing:
                return OrderOut.from_orm_model(existing)
            raise

    async def get_user_orders(
        self,
        user_id: str,
        params: OrderListParams,
    ) -> dict:
        orders, total = await self.order_repo.list_by_user(
            user_id=user_id,
            status=params.status,
            page=params.page,
            limit=params.limit,
        )
        return {
            "orders": [OrderOut.from_orm_model(o) for o in orders],
            "total": total,
            "page": params.page,
            "limit": params.limit,
        }

    async def get_order(self, order_id: str, user_id: str) -> OrderOut:
        order = await self.order_repo.get_by_id(order_id)
        if not order:
            raise NotFoundError("Order")
        if order.user_id != user_id:
            raise ForbiddenError(
                "You do not have permission to view this order",
            )
        return OrderOut.from_orm_model(order)

    async def get_all_orders(self, params: OrderListParams) -> dict:
        orders, total = await self.order_repo.list_all(
            status=params.status,
            event_id=params.eventId,
            page=params.page,
            limit=params.limit,
        )
        return {
            "orders": [OrderOut.from_orm_model(o) for o in orders],
            "total": total,
            "page": params.page,
            "limit": params.limit,
        }
