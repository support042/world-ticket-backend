from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
from app.db.session import get_db
from app.schemas.common import ApiResponse
from app.schemas.event import CreateInitiationRequest
from app.services.section_payment_service import SectionPaymentService

router = APIRouter(prefix="/sections", tags=["Sections"])


@router.post("/{section_id}/payment-initiated", status_code=201)
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
