from app.models.state import BookingGraphState


async def confirm_slot(state: BookingGraphState) -> BookingGraphState:
    state["selected_slot"] = {
        "start_time": state.get("intent", {}).get("time_preference"),
        "timezone": "Asia/Hong_Kong",
        "confirmation_required": True,
    }
    return state
