from fastapi import APIRouter

from app.agents.booking_graph import run_booking_graph
from app.models.booking import BookingRequest, BookingResponse

router = APIRouter()


@router.post("", response_model=BookingResponse)
async def create_booking(request: BookingRequest) -> BookingResponse:
    return await run_booking_graph(request)
