from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.mixins import TimestampMixin, generate_id
from app.db.session import Base


class Event(Base, TimestampMixin):
    __tablename__ = "events"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: generate_id("evt"),
    )
    title: Mapped[str] = mapped_column(String(300), nullable=False, index=True)
    tournament: Mapped[str] = mapped_column(String(200), nullable=False)
    stage: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    date: Mapped[str] = mapped_column(String(10), nullable=False)
    time: Mapped[str] = mapped_column(String(5), nullable=False)
    venue: Mapped[str] = mapped_column(String(200), nullable=False)
    city: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    state: Mapped[str | None] = mapped_column(String(100), nullable=True)
    is_paid: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    payment_initiated: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    payment_link: Mapped[str | None] = mapped_column(Text, nullable=True)
    country: Mapped[str] = mapped_column(String(100), nullable=False)
    image: Mapped[str | None] = mapped_column(Text, nullable=True)
    tickets_left_percent: Mapped[int] = mapped_column(
        Integer,
        default=100,
        nullable=False,
    )
    views_last_hour: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    favorites: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    price_min: Mapped[float] = mapped_column(Float, nullable=False)
    price_max: Mapped[float] = mapped_column(Float, nullable=False)
    teams: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    categories: Mapped[list] = mapped_column(
        JSONB,
        default=list,
        nullable=False,
    )
    settings: Mapped[dict] = mapped_column(
        JSONB,
        default=lambda: {
            "ticketLimitPerUser": 6,
            "allowResale": False,
            "requireId": True,
        },
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(20),
        default="upcoming",
        nullable=False,
        index=True,
    )


class Section(Base, TimestampMixin):
    __tablename__ = "sections"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: generate_id("sec"),
    )
    event_id: Mapped[str] = mapped_column(
        String(36),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    row: Mapped[str] = mapped_column(String(10), nullable=False)
    price: Mapped[float] = mapped_column(Float, nullable=False)
    available: Mapped[int] = mapped_column(Integer, nullable=False)
    capacity: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(
        String(10),
        default="USD",
        nullable=False,
    )
    is_popular: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    is_lowest_price: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    features: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    perks: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    section_image: Mapped[str | None] = mapped_column(Text, nullable=True)


class SectionPaymentInitiation(Base, TimestampMixin):
    __tablename__ = "section_payment_initiations"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: generate_id("spi"),
    )
    user_id: Mapped[str] = mapped_column(
        String(36),
        nullable=False,
        index=True,
    )
    event_id: Mapped[str] = mapped_column(
        String(36),
        nullable=False,
        index=True,
    )
    section_id: Mapped[str] = mapped_column(
        String(36),
        nullable=False,
        index=True,
    )
    payment_initiated: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    is_paid: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    payment_link: Mapped[str | None] = mapped_column(Text, nullable=True)
    initiated_at: Mapped[str | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[str | None] = mapped_column(DateTime(timezone=True), nullable=True)
