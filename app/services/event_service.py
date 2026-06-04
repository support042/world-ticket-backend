import json

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.infrastructure.cache import cache
from app.repositories.event_repository import (
    EventRepository,
    SectionRepository,
)
from app.schemas.event import (
    CreateEventRequest,
    CreateSectionRequest,
    EventListParams,
    EventOut,
    SectionOut,
    UpdateEventRequest,
    UpdateSectionRequest,
)

_EVENT_CACHE_TTL = 300
_LIST_CACHE_TTL = 120


def _event_cache_key(event_id: str) -> str:
    return f"event:{event_id}"


def _sections_cache_key(event_id: str) -> str:
    return f"sections:{event_id}"


class EventService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.event_repo = EventRepository(db)
        self.section_repo = SectionRepository(db)

    async def list_events(self, params: EventListParams) -> dict:
        events, total = await self.event_repo.list_events(
            search=params.search,
            location=params.location,
            team=params.team,
            stage=params.stage,
            price_min=params.priceMin,
            price_max=params.priceMax,
            page=params.page,
            limit=params.limit,
        )
        return {
            "events": [
                EventOut.from_orm_model(
                    e,
                    sections=[],
                )
                for e in events
            ],
            "total": total,
            "page": params.page,
            "limit": params.limit,
            "hasMore": (params.page * params.limit) < total,
        }

    async def get_event(self, event_id: str) -> EventOut:
        cached = await cache.get(_event_cache_key(event_id))
        if cached:
            return EventOut.model_validate_json(cached)

        event = await self.event_repo.get_by_id(event_id)
        if not event:
            raise NotFoundError("Event")
        sections = await self.section_repo.get_by_event(event_id)
        out = EventOut.from_orm_model(event, sections=sections)
        await cache.set(
            _event_cache_key(event_id),
            out.model_dump_json(),
            ttl=_EVENT_CACHE_TTL,
        )
        return out

    async def get_sections(self, event_id: str) -> list[SectionOut]:
        cached = await cache.get(_sections_cache_key(event_id))
        if cached:
            data = json.loads(cached)
            return [SectionOut.model_validate(s) for s in data]

        event = await self.event_repo.get_by_id(event_id)
        if not event:
            raise NotFoundError("Event")
        sections = await self.section_repo.get_by_event(event_id)
        out = [SectionOut.from_orm_model(s) for s in sections]
        payload = json.dumps([s.model_dump() for s in out])
        await cache.set(
            _sections_cache_key(event_id),
            payload,
            ttl=_LIST_CACHE_TTL,
        )
        return out

    async def create_event(self, payload: CreateEventRequest) -> EventOut:
        event = await self.event_repo.create(
            title=payload.title,
            tournament=payload.tournament,
            stage=payload.stage,
            date=payload.date,
            time=payload.time,
            venue=payload.venue,
            city=payload.city,
            state=payload.state,
            country=payload.country,
            image=payload.image,
            tickets_left_percent=payload.ticketsLeftPercent,
            views_last_hour=0,
            favorites=0,
            price_min=payload.priceRange.min,
            price_max=payload.priceRange.max,
            teams=[t.model_dump() for t in payload.teams],
            categories=[c.model_dump() for c in payload.categories],
            settings=payload.settings.model_dump(),
            status=payload.status,
        )
        return EventOut.from_orm_model(event, sections=[])

    async def update_event(
        self,
        event_id: str,
        payload: UpdateEventRequest,
    ) -> EventOut:
        event = await self.event_repo.get_by_id(event_id)
        if not event:
            raise NotFoundError("Event")

        updates: dict = {}
        if payload.title is not None:
            updates["title"] = payload.title
        if payload.tournament is not None:
            updates["tournament"] = payload.tournament
        if payload.stage is not None:
            updates["stage"] = payload.stage
        if payload.date is not None:
            updates["date"] = payload.date
        if payload.time is not None:
            updates["time"] = payload.time
        if payload.venue is not None:
            updates["venue"] = payload.venue
        if payload.city is not None:
            updates["city"] = payload.city
        if payload.state is not None:
            updates["state"] = payload.state
        if payload.country is not None:
            updates["country"] = payload.country
        if payload.image is not None:
            updates["image"] = payload.image
        if payload.ticketsLeftPercent is not None:
            updates["tickets_left_percent"] = payload.ticketsLeftPercent
        if payload.priceRange is not None:
            updates["price_min"] = payload.priceRange.min
            updates["price_max"] = payload.priceRange.max
        if payload.teams is not None:
            updates["teams"] = [t.model_dump() for t in payload.teams]
        if payload.categories is not None:
            updates["categories"] = [c.model_dump() for c in payload.categories]
        if payload.settings is not None:
            updates["settings"] = payload.settings.model_dump()
        if payload.status is not None:
            updates["status"] = payload.status

        event = await self.event_repo.update(event, updates)
        await cache.delete(_event_cache_key(event_id))
        await cache.delete(_sections_cache_key(event_id))
        sections = await self.section_repo.get_by_event(event_id)
        return EventOut.from_orm_model(event, sections=sections)

    async def delete_event(self, event_id: str) -> None:
        event = await self.event_repo.get_by_id(event_id)
        if not event:
            raise NotFoundError("Event")
        await self.event_repo.delete(event)
        await cache.delete(_event_cache_key(event_id))
        await cache.delete(_sections_cache_key(event_id))

    async def add_section(
        self,
        event_id: str,
        payload: CreateSectionRequest,
    ) -> SectionOut:
        event = await self.event_repo.get_by_id(event_id)
        if not event:
            raise NotFoundError("Event")
        section = await self.section_repo.create(
            event_id=event_id,
            name=payload.name,
            row=payload.row,
            price=payload.price,
            available=payload.available,
            capacity=payload.capacity,
            currency=payload.currency,
            payment_link=payload.payment_link,
            is_popular=payload.isPopular,
            is_lowest_price=payload.isLowestPrice,
            features=payload.features,
            perks=payload.perks,
            section_image=payload.sectionImage,
        )
        await cache.delete(_sections_cache_key(event_id))
        await cache.delete(_event_cache_key(event_id))
        return SectionOut.from_orm_model(section)

    async def update_section(
        self, event_id: str, section_id: str, payload: UpdateSectionRequest
    ) -> SectionOut:
        section = await self.section_repo.get_by_id(section_id)
        if not section or section.event_id != event_id:
            raise NotFoundError("Section")

        updates: dict = {}
        if payload.name is not None:
            updates["name"] = payload.name
        if payload.row is not None:
            updates["row"] = payload.row
        if payload.price is not None:
            updates["price"] = payload.price
        if payload.available is not None:
            updates["available"] = payload.available
        if payload.capacity is not None:
            updates["capacity"] = payload.capacity
        if payload.currency is not None:
            updates["currency"] = payload.currency
        if payload.payment_link is not None:
            updates["payment_link"] = payload.payment_link
        if payload.isPopular is not None:
            updates["is_popular"] = payload.isPopular
        if payload.isLowestPrice is not None:
            updates["is_lowest_price"] = payload.isLowestPrice
        if payload.features is not None:
            updates["features"] = payload.features
        if payload.perks is not None:
            updates["perks"] = payload.perks
        if payload.sectionImage is not None:
            updates["section_image"] = payload.sectionImage

        section = await self.section_repo.update(section, updates)
        await cache.delete(_sections_cache_key(event_id))
        await cache.delete(_event_cache_key(event_id))
        return SectionOut.from_orm_model(section)

    async def delete_section(self, event_id: str, section_id: str) -> None:
        section = await self.section_repo.get_by_id(section_id)
        if not section or section.event_id != event_id:
            raise NotFoundError("Section")
        await self.section_repo.delete(section)
        await cache.delete(_sections_cache_key(event_id))
        await cache.delete(_event_cache_key(event_id))
