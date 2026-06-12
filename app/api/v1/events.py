from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
from app.db.session import get_db
from app.schemas.common import ApiResponse
from app.schemas.event import EventListParams, UserInitiationListOut, CreateInitiationRequest
from app.services.event_service import EventService
from app.services.section_payment_service import SectionPaymentService

router = APIRouter(prefix="", tags=["Events"])


@router.get("/events", summary="List all events")
async def list_events(
    search: str | None = Query(None),
    location: str | None = Query(None),
    team: str | None = Query(None),
    stage: str | None = Query(None),
    priceMin: float | None = Query(None),
    priceMax: float | None = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse:
    params = EventListParams(
        search=search,
        location=location,
        team=team,
        stage=stage,
        priceMin=priceMin,
        priceMax=priceMax,
        page=page,
        limit=limit,
    )
    service = EventService(db)
    data = await service.list_events(params)
    return ApiResponse.ok(data=data)


@router.get("/events/{event_id}", summary="Get single event details")
async def get_event(
    event_id: str,
    db: AsyncSession = Depends(get_db),
) -> ApiResponse:
    service = EventService(db)
    event = await service.get_event(event_id)
    return ApiResponse.ok(data={"event": event.model_dump()})


@router.get("/events/{event_id}/sections", summary="Get sections for an event")
async def get_sections(
    event_id: str,
    db: AsyncSession = Depends(get_db),
) -> ApiResponse:
    service = EventService(db)
    sections = await service.get_sections(event_id)
    return ApiResponse.ok(data={"sections": [s.model_dump() for s in sections]})  # noqa: S106, E501


@router.get(
    "/sections/my-initiated-payments",
    summary="List user's initiated payments",
    responses={200: {"model": ApiResponse[UserInitiationListOut]}},
)
async def list_user_payment_initiated(
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse:
    service = SectionPaymentService(db)
    data = await service.list_initiated_for_user(user.id, page=page, limit=limit)  # noqa: E501
    return ApiResponse.ok(data=data)


@router.post("/sections/{section_id}/payment-initiated", status_code=201)
async def initiate_section_payment(
    section_id: str,
    payload: CreateInitiationRequest,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse:
    service = SectionPaymentService(db)
    spi = await service.initiate_payment(current_user, section_id, payload.paymentLink)
    return ApiResponse.ok(
        data={
            "initiation": {
                "id": spi.id,
                "sectionId": spi.section_id,
                "eventId": spi.event_id,
                "initiatedAt": spi.initiated_at.isoformat() if spi.initiated_at else None,
                "paymentLink": spi.payment_link,
            }
        }
    )

