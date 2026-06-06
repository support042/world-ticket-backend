from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.event import Event, Section, SectionPaymentInitiation
from app.models.user import User


class SectionPaymentInitiationRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(self, **kwargs) -> SectionPaymentInitiation:
        spi = SectionPaymentInitiation(**kwargs)
        self.db.add(spi)
        await self.db.flush()
        await self.db.refresh(spi)
        return spi

    async def get_by_id(self, spi_id: str) -> SectionPaymentInitiation | None:
        result = await self.db.execute(
            select(SectionPaymentInitiation).where(SectionPaymentInitiation.id == spi_id)  # noqa: S106, E501
        )
        return result.scalar_one_or_none()

    async def update(
        self, spi: SectionPaymentInitiation, updates: dict
    ) -> SectionPaymentInitiation:
        for key, value in updates.items():
            setattr(spi, key, value)
        await self.db.flush()
        await self.db.refresh(spi)
        return spi

    async def list_initiated_for_admin(self, page: int, limit: int):
        base_where = SectionPaymentInitiation.payment_initiated.is_(True)

        stmt = (
            select(User, SectionPaymentInitiation, Section, Event)
            .join(SectionPaymentInitiation, User.id == SectionPaymentInitiation.user_id)  # noqa: S106, E501
            .join(Section, Section.id == SectionPaymentInitiation.section_id)
            .join(Event, Event.id == SectionPaymentInitiation.event_id)
            .where(base_where)
            .order_by(SectionPaymentInitiation.initiated_at.desc())
            .offset((page - 1) * limit)
            .limit(limit)
        )

        count_stmt = select(func.count()).select_from(SectionPaymentInitiation).where(base_where)  # noqa: S106, E501

        result = await self.db.execute(stmt)
        rows = result.all()

        total_result = await self.db.execute(count_stmt)
        total = total_result.scalar_one()

        return rows, total

    async def list_by_user(self, user_id: str, page: int, limit: int):
        stmt = (
            select(SectionPaymentInitiation)
            .where(SectionPaymentInitiation.user_id == user_id)
            .order_by(SectionPaymentInitiation.created_at.desc())
            .offset((page - 1) * limit)
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def list_initiated_for_user(
        self,
        page: int,
        limit: int,
        user_id: str,
    ):
        base_where = and_(
            SectionPaymentInitiation.payment_initiated.is_(True),
            SectionPaymentInitiation.user_id == user_id,
        )

        stmt = (
            select(User, SectionPaymentInitiation, Section, Event)
            .join(
                SectionPaymentInitiation,
                User.id == SectionPaymentInitiation.user_id,
            )
            .join(Section, Section.id == SectionPaymentInitiation.section_id)
            .join(Event, Event.id == SectionPaymentInitiation.event_id)
            .where(base_where)
            .order_by(SectionPaymentInitiation.initiated_at.desc())
            .offset((page - 1) * limit)
            .limit(limit)
        )

        count_stmt = select(func.count()).select_from(SectionPaymentInitiation).where(base_where)  # noqa: S106, E501

        result = await self.db.execute(stmt)
        rows = result.all()

        total_result = await self.db.execute(count_stmt)
        total = total_result.scalar_one()

        return rows, total
