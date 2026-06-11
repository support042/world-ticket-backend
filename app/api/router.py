from fastapi import APIRouter

from app.api.v1 import (
    admin,
    auth,
    checkout,
    events,
    orders,
    payments,
    webhooks,
)

api_router = APIRouter(prefix="/api")

api_router.include_router(auth.router)
api_router.include_router(events.router)
api_router.include_router(checkout.router)
api_router.include_router(orders.router)
api_router.include_router(admin.router)
api_router.include_router(payments.router)
api_router.include_router(webhooks.router)
