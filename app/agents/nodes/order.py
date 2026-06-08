from uuid import uuid4

from app.models.state import BookingGraphState


async def create_order(state: BookingGraphState) -> BookingGraphState:
    state["order"] = {
        "task_id": f"task_{uuid4().hex[:12]}",
        "status": "draft",
        "slot": state.get("selected_slot"),
        "provider": (state.get("service_candidates") or [{}])[0],
    }
    return state
