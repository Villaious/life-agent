from app.models.state import BookingGraphState


async def understand_intent(state: BookingGraphState) -> BookingGraphState:
    request = state["request"]
    missing_fields: list[str] = []

    if not request.message.strip():
        missing_fields.append("service_intent")

    state["intent"] = {
        "raw_text": request.message,
        "service_category": "unknown",
        "location": request.context.get("location"),
        "time_preference": request.context.get("time_preference"),
    }

    if not state["intent"]["location"]:
        missing_fields.append("location")
    if not state["intent"]["time_preference"]:
        missing_fields.append("time_preference")

    state["missing_fields"] = missing_fields
    return state
