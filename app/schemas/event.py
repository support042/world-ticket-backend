from datetime import datetime

from pydantic import BaseModel, field_validator


class TeamSchema(BaseModel):
    name: str
    code: str
    flag: str

    @field_validator("code")
    @classmethod
    def code_uppercase(cls, v: str) -> str:
        return v.upper()


class CategorySchema(BaseModel):
    id: int
    name: str
    price: float
    color: str
    available: int


class SectionOut(BaseModel):
    id: str
    name: str
    row: str
    price: float
    is_paid: bool
    payment_initiated: bool
    payment_link: str | None
    available: int
    capacity: int
    currency: str
    isPopular: bool
    isLowestPrice: bool
    features: list[str]
    perks: list[str]
    sectionImage: str | None

    @classmethod
    def from_orm_model(cls, section) -> "SectionOut":
        return cls(
            id=section.id,
            name=section.name,
            row=section.row,
            price=section.price,
            available=section.available,
            capacity=section.capacity,
            currency=section.currency,
            isPopular=section.is_popular,
            isLowestPrice=section.is_lowest_price,
            features=section.features,
            perks=section.perks,
            sectionImage=section.section_image,
        )


class EventSettingsSchema(BaseModel):
    ticketLimitPerUser: int = 6
    allowResale: bool = False
    requireId: bool = True


class PriceRangeSchema(BaseModel):
    min: float
    max: float


class EventOut(BaseModel):
    id: str
    title: str
    tournament: str
    stage: str
    date: str
    time: str
    venue: str
    city: str
    state: str | None
    country: str
    image: str | None
    ticketsLeftPercent: int
    viewsLastHour: int
    favorites: int
    priceRange: PriceRangeSchema
    teams: list[TeamSchema]
    categories: list[CategorySchema]
    sections: list[SectionOut]
    settings: EventSettingsSchema
    status: str
    createdAt: datetime
    updatedAt: datetime | None = None

    @classmethod
    def from_orm_model(cls, event, sections: list | None = None) -> "EventOut":
        return cls(
            id=event.id,
            title=event.title,
            tournament=event.tournament,
            stage=event.stage,
            date=event.date,
            time=event.time,
            venue=event.venue,
            city=event.city,
            state=event.state,
            country=event.country,
            image=event.image,
            ticketsLeftPercent=event.tickets_left_percent,
            viewsLastHour=event.views_last_hour,
            favorites=event.favorites,
            priceRange=PriceRangeSchema(
                min=event.price_min,
                max=event.price_max,
            ),
            teams=[TeamSchema(**t) for t in (event.teams or [])],
            categories=[CategorySchema(**c) for c in (event.categories or [])],
            sections=[SectionOut.from_orm_model(s) for s in (sections or [])],
            settings=EventSettingsSchema(**(event.settings or {})),
            status=event.status,
            createdAt=event.created_at,
            updatedAt=event.updated_at,
        )


class CreateEventRequest(BaseModel):
    title: str
    tournament: str
    stage: str
    date: str
    time: str
    venue: str
    city: str
    state: str | None = None
    country: str
    image: str | None = None
    ticketsLeftPercent: int = 100
    priceRange: PriceRangeSchema
    teams: list[TeamSchema]
    categories: list[CategorySchema] = []
    settings: EventSettingsSchema = EventSettingsSchema()
    status: str = "upcoming"

    @field_validator("date")
    @classmethod
    def validate_date(cls, v: str) -> str:
        import re

        if not re.match(r"^\d{4}-\d{2}-\d{2}$", v):
            raise ValueError("Date must be YYYY-MM-DD")
        return v

    @field_validator("time")
    @classmethod
    def validate_time(cls, v: str) -> str:
        import re

        if not re.match(r"^\d{2}:\d{2}$", v):
            raise ValueError("Time must be HH:MM")
        return v

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        allowed = {"upcoming", "ongoing", "completed", "cancelled"}
        if v not in allowed:
            raise ValueError(f"Status must be one of {allowed}")
        return v


class UpdateEventRequest(BaseModel):
    title: str | None = None
    tournament: str | None = None
    stage: str | None = None
    date: str | None = None
    time: str | None = None
    venue: str | None = None
    city: str | None = None
    state: str | None = None
    country: str | None = None
    image: str | None = None
    ticketsLeftPercent: int | None = None
    priceRange: PriceRangeSchema | None = None
    teams: list[TeamSchema] | None = None
    categories: list[CategorySchema] | None = None
    settings: EventSettingsSchema | None = None
    status: str | None = None

    @field_validator("status", mode="before")
    @classmethod
    def validate_status(cls, v: str | None) -> str | None:
        if v is None:
            return v
        allowed = {"upcoming", "ongoing", "completed", "cancelled"}
        if v not in allowed:
            raise ValueError(f"Status must be one of {allowed}")
        return v


class CreateSectionRequest(BaseModel):
    name: str
    row: str
    price: float
    available: int
    capacity: int
    currency: str = "USD"
    isPopular: bool = False
    payment_link: str | None = None
    isLowestPrice: bool = False
    features: list[str] = []
    perks: list[str] = []
    sectionImage: str | None = None


class UpdateSectionRequest(BaseModel):
    name: str | None = None
    row: str | None = None
    price: float | None = None
    available: int | None = None
    capacity: int | None = None
    payment_link: str | None = None
    currency: str | None = None
    isPopular: bool | None = None
    isLowestPrice: bool | None = None
    features: list[str] | None = None
    perks: list[str] | None = None
    sectionImage: str | None = None


class CreateInitiationRequest(BaseModel):
    paymentLink: str | None = None


class InitiatedSectionSchema(BaseModel):
    initiationId: str
    sectionId: str
    sectionName: str
    eventId: str
    eventTitle: str
    initiatedAt: datetime | None
    isPaid: bool
    paymentLink: str | None


class AdminInitiatedUserOut(BaseModel):
    userId: str
    email: str
    firstName: str
    lastName: str
    initiatedSections: list[InitiatedSectionSchema]


class AdminInitiationListOut(BaseModel):
    users: list[AdminInitiatedUserOut]
    total: int
    page: int
    limit: int


class EventListParams(BaseModel):
    search: str | None = None
    location: str | None = None
    team: str | None = None
    stage: str | None = None
    priceMin: float | None = None
    priceMax: float | None = None
    page: int = 1
    limit: int = 20

    @field_validator("page")
    @classmethod
    def page_positive(cls, v: int) -> int:
        return max(1, v)

    @field_validator("limit")
    @classmethod
    def limit_range(cls, v: int) -> int:
        return min(max(1, v), 100)
