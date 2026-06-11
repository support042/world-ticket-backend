import asyncio

import stripe
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import NotFoundError, ValidationError
from app.repositories.event_repository import (
    EventRepository,
    SectionRepository,
)
from app.schemas.checkout import CheckoutIntentRequest, CheckoutIntentResponse

stripe.api_key = settings.STRIPE_SECRET_KEY

_SERVICE_FEE_PERCENT = 0.05


class CheckoutService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.event_repo = EventRepository(db)
        self.section_repo = SectionRepository(db)

    async def create_payment_intent(
        self,
        payload: CheckoutIntentRequest,
    ) -> CheckoutIntentResponse:
        section = await self.section_repo.get_by_id(payload.sectionId)
        if not section:
            raise NotFoundError("Section")

        event = await self.event_repo.get_by_id(payload.eventId)
        if not event:
            raise NotFoundError("Event")

        if section.event_id != payload.eventId:
            raise ValidationError("Section does not belong to this event")

        if section.available < payload.quantity:
            raise ValidationError(
                f"Only {section.available} tickets available for this section",
            )

        base_amount = section.price * payload.quantity
        fee = round(base_amount * _SERVICE_FEE_PERCENT, 2)
        total = base_amount + fee
        amount_cents = int(round(total * 100))

        intent = await asyncio.to_thread(
            stripe.PaymentIntent.create,
            amount=amount_cents,
            currency=payload.currency.lower(),
            metadata={
                "eventId": payload.eventId,
                "sectionId": payload.sectionId,
                "quantity": str(payload.quantity),
            },
        )

        return CheckoutIntentResponse(
            clientSecret=intent.client_secret,
            amount=amount_cents,
            currency=payload.currency.lower(),
        )
