from app.core.config import settings
from app.db.repositories import (
    save_booking_order,
    save_booking_task,
    save_order_action_result,
    save_tool_audit_log,
)
from app.db.session import SessionLocal
from app.models.booking import BookingResponse, BookingStatus
from app.models.state import BookingGraphState


class BookingPersistenceService:
    def __init__(self, enabled: bool | None = None) -> None:
        self.enabled = settings.booking_persistence_enabled if enabled is None else enabled

    async def save_final_state(self, state: BookingGraphState, response: BookingResponse) -> None:
        if not self.enabled:
            return

        try:
            async with SessionLocal.begin() as session:
                await save_booking_task(session, state, response)
                if response.status == BookingStatus.CREATED and state.get("order"):
                    request = state["request"]
                    await save_booking_order(session, request.user_id, request.session_id, state["order"])
                if response.status == BookingStatus.COMPLETED and state.get("action_result"):
                    request = state["request"]
                    await save_order_action_result(
                        session,
                        request.user_id,
                        request.session_id,
                        state["action_result"],
                    )

                context = state["tool_context"]
                for event in state.get("audit_events", []):
                    await save_tool_audit_log(session, context, event)
        except Exception:
            return
