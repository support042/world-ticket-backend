from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_admin
from app.db.session import get_db
from app.schemas.common import ApiResponse
from app.schemas.event import (
    CreateEventRequest,
    CreateSectionRequest,
    UpdateEventRequest,
    UpdateSectionRequest,
)
from app.schemas.order import OrderListParams
from app.services.event_service import EventService
from app.services.order_service import OrderService
from app.services.section_payment_service import SectionPaymentService

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.post("/events", status_code=201, summary="Create event")
async def create_event(
    payload: CreateEventRequest,
    _admin=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse:
    service = EventService(db)
    event = await service.create_event(payload)
    return ApiResponse.ok(
        data={"event": event.model_dump()},
        message="Event created successfully",
    )


@router.put("/events/{event_id}", summary="Update event")
async def update_event(
    event_id: str,
    payload: UpdateEventRequest,
    _admin=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse:
    service = EventService(db)
    event = await service.update_event(event_id, payload)
    return ApiResponse.ok(
        data={"event": event.model_dump()},
        message="Event updated successfully",
    )


@router.delete("/events/{event_id}", summary="Delete event")
async def delete_event(
    event_id: str,
    _admin=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse:
    service = EventService(db)
    await service.delete_event(event_id)
    return ApiResponse.ok(data=None, message="Event deleted successfully")


@router.post(
    "/events/{event_id}/sections",
    status_code=201,
    summary="Add section to event",
)
async def add_section(
    event_id: str,
    payload: CreateSectionRequest,
    _admin=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse:
    service = EventService(db)
    section = await service.add_section(event_id, payload)
    return ApiResponse.ok(
        data={"section": section.model_dump()},
        message="Section added successfully",
    )


@router.put(
    "/events/{event_id}/sections/{section_id}",
    summary="Update section",
)
async def update_section(
    event_id: str,
    section_id: str,
    payload: UpdateSectionRequest,
    _admin=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse:
    service = EventService(db)
    section = await service.update_section(event_id, section_id, payload)
    return ApiResponse.ok(data={"section": section.model_dump()})


@router.delete(
    "/events/{event_id}/sections/{section_id}",
    summary="Delete section",
)
async def delete_section(
    event_id: str,
    section_id: str,
    _admin=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse:
    service = EventService(db)
    await service.delete_section(event_id, section_id)
    return ApiResponse.ok(
        data=None,
        message="Section deleted successfully",
    )


@router.get("/orders", summary="Get all platform orders")
async def get_all_orders(
    status: str | None = Query(None),
    eventId: str | None = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    _admin=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse:
    params = OrderListParams(
        status=status,
        eventId=eventId,
        page=page,
        limit=limit,
    )
    service = OrderService(db)
    data = await service.get_all_orders(params)
    return ApiResponse.ok(data=data)


@router.get(
    "/payment-initiated-users",
    summary="List users with initiated payments",
)
async def list_payment_initiated_users(
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    _admin=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse:
    service = SectionPaymentService(db)
    data = await service.list_initiated_for_admin(page=page, limit=limit)
    return ApiResponse.ok(data=data)


@router.post(
    "/section-payments/{initiation_id}/mark-paid",
    summary="Mark a payment initiation as paid",
)
async def mark_payment_paid(
    initiation_id: str,
    _admin=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse:
    service = SectionPaymentService(db)
    spi = await service.mark_paid(initiation_id)
    return ApiResponse.ok(
        data={
            "initiation": {
                "id": spi.id,
                "isPaid": spi.is_paid,
                "completedAt": spi.completed_at.isoformat() if spi.completed_at else None,  # noqa: S106, E501
            }
        }
    )
