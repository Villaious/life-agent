from fastapi import APIRouter

from app.api.v1.bookings import router as bookings_router
from app.api.v1.health import router as health_router

router = APIRouter()
router.include_router(health_router, tags=["health"])
router.include_router(bookings_router, prefix="/v1/bookings", tags=["bookings"])
