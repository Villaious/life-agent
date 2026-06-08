from app.agents.booking_agent import BookingAgent
from app.models.booking import BookingRequest, BookingResponse


async def run_booking_graph(request: BookingRequest) -> BookingResponse:
    agent = BookingAgent()
    return await agent.run(request.message, request=request)
