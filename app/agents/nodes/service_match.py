from app.models.state import BookingGraphState


async def match_service(state: BookingGraphState) -> BookingGraphState:
    state["service_candidates"] = [
        {
            "provider_id": "provider_demo_001",
            "name": "示例本地服务商",
            "category": state.get("intent", {}).get("service_category", "unknown"),
            "score": 0.82,
        }
    ]
    return state
