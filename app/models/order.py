from sqlalchemy import Boolean, Float, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.mixins import TimestampMixin, generate_id
from app.db.session import Base


class Order(Base, TimestampMixin):
    __tablename__ = "orders"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: generate_id("ord"),
    )
    user_id: Mapped[str | None] = mapped_column(
        String(36),
        nullable=True,
        index=True,
    )
    event_id: Mapped[str] = mapped_column(
        String(36),
        nullable=False,
        index=True,
    )
    section_id: Mapped[str] = mapped_column(String(36), nullable=False)
    event_snapshot: Mapped[dict] = mapped_column(JSONB, nullable=False)
    section_snapshot: Mapped[dict] = mapped_column(JSONB, nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    contact_info: Mapped[dict] = mapped_column(JSONB, nullable=False)
    total_amount: Mapped[float] = mapped_column(Float, nullable=False)
    payment_method: Mapped[str] = mapped_column(String(30), nullable=False)
    stripe_payment_intent_id: Mapped[str] = mapped_column(
        String(200),
        unique=True,
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(20),
        default="processing",
        nullable=False,
        index=True,
    )
    tickets: Mapped[list | None] = mapped_column(JSONB, nullable=True, default=list)
    gift_option: Mapped[bool] = mapped_column(Boolean, nullable=True, default=False)
    team_support: Mapped[str | None] = mapped_column(String(100), nullable=True)
