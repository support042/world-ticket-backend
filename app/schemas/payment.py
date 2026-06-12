from datetime import datetime
from pydantic import BaseModel, EmailStr, field_validator
from app.schemas.order import ContactInfoSchema


class CreateCheckoutSessionRequest(BaseModel):
    sectionId: str
    quantity: int
    contactInfo: ContactInfoSchema
    giftOption: bool = False
    teamSupport: str | None = None

    @field_validator("quantity")
    @classmethod
    def quantity_positive(cls, v: int) -> int:
        if v < 1:
            raise ValueError("Quantity must be at least 1")
        return v


class CheckoutSessionResponse(BaseModel):
    sessionId: str
    checkoutUrl: str


class TicketSchema(BaseModel):
    id: str
    barcode: str


class VerificationSectionSchema(BaseModel):
    id: str
    name: str
    row: str
    eventTitle: str
    eventDate: str


class VerificationOrderSchema(BaseModel):
    id: str
    status: str
    quantity: int
    totalAmount: float
    section: VerificationSectionSchema
    tickets: list[TicketSchema]
    contactInfo: dict  # e.g., {"email": "john@example.com"}


class SessionVerificationResponse(BaseModel):
    sessionId: str
    status: str
    amountTotal: int
    currency: str
    order: VerificationOrderSchema | None = None


class PaymentOrderSectionSchema(BaseModel):
    id: str
    name: str
    row: str


class PaymentOrderEventSchema(BaseModel):
    id: str
    title: str
    date: str
    venue: str
    city: str


class PaymentOrderOut(BaseModel):
    id: str
    stripeSessionId: str
    status: str
    quantity: int
    totalAmount: float
    createdAt: datetime
    section: PaymentOrderSectionSchema
    event: PaymentOrderEventSchema
    tickets: list[TicketSchema]
