from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
from app.db.session import get_db
from app.schemas.common import ApiResponse
from app.schemas.event import EventListParams, UserInitiationListOut
from app.services.event_service import EventService
from app.services.section_payment_service import SectionPaymentService

router = APIRouter(prefix="/events", tags=["Events"])


@router.get("", summary="List all events")
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


@router.get("/{event_id}", summary="Get single event details")
async def get_event(
    event_id: str,
    db: AsyncSession = Depends(get_db),
) -> ApiResponse:
    service = EventService(db)
    event = await service.get_event(event_id)
    return ApiResponse.ok(data={"event": event.model_dump()})


@router.get("/{event_id}/sections", summary="Get sections for an event")
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
    data = await service.list_initiated_for_user(user, page=page, limit=limit)
    return ApiResponse.ok(data=data)
