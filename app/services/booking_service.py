from app.models.booking import BookingRequest, BookingResponse
from app.agents.booking_graph import run_booking_graph


class BookingService:
    async def create_booking(self, request: BookingRequest) -> BookingResponse:
        return await run_booking_graph(request)
