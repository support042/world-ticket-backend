from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.repositories.event_repository import EventRepository, SectionRepository
from app.repositories.section_payment_repository import SectionPaymentInitiationRepository


class SectionPaymentService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.spi_repo = SectionPaymentInitiationRepository(db)
        self.event_repo = EventRepository(db)
        self.section_repo = SectionRepository(db)

    async def initiate_payment(self, user, section_id: str, payment_link: str | None = None):
        section = await self.section_repo.get_by_id(section_id)
        if not section:
            raise NotFoundError("Section")
        event = await self.event_repo.get_by_id(section.event_id)
        if not event:
            raise NotFoundError("Event")

        spi = await self.spi_repo.create(
            user_id=user.id,
            event_id=section.event_id,
            section_id=section_id,
            payment_initiated=True,
            payment_link=payment_link,
            initiated_at=datetime.utcnow(),
        )
        return spi

    async def list_initiated_for_admin(self, page: int = 1, limit: int = 50):
        rows, total = await self.spi_repo.list_initiated_for_admin(page, limit)
        # rows are tuples (User, SPI, Section, Event)
        users_map: dict = {}
        total_items = total
        for user, spi, section, event in rows:
            uid = user.id
            users_map.setdefault(
                uid,
                {
                    "userId": uid,
                    "email": user.email,
                    "firstName": user.first_name,
                    "lastName": user.last_name,
                    "initiatedSections": [],
                },
            )
            users_map[uid]["initiatedSections"].append(
                {
                    "initiationId": spi.id,
                    "sectionId": section.id,
                    "sectionName": section.name,
                    "eventId": event.id,
                    "eventTitle": event.title,
                    "initiatedAt": spi.initiated_at.isoformat() if spi.initiated_at else None,
                    "isPaid": spi.is_paid,
                    "paymentLink": spi.payment_link,
                }
            )

        return {
            "users": list(users_map.values()),
            "total": total_items,
            "page": page,
            "limit": limit,
        }

    async def mark_paid(self, initiation_id: str):
        spi = await self.spi_repo.get_by_id(initiation_id)
        if not spi:
            raise NotFoundError("SectionPaymentInitiation")
        updates = {"is_paid": True, "completed_at": datetime.utcnow()}
        spi = await self.spi_repo.update(spi, updates)
        return spi
