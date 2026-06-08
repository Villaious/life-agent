from typing import Any, TypedDict

from app.models.booking import (
    AppointmentSlot,
    BookingRequest,
    BookingResponse,
    DraftOrder,
    OrderActionResult,
    ServiceCandidate,
)
from app.tools.policy import ToolContext


class BookingGraphState(TypedDict, total=False):
    request: BookingRequest
    tool_context: ToolContext
    intent: dict[str, Any]
    missing_fields: list[str]
    service_candidates: list[ServiceCandidate]
    selected_slot: AppointmentSlot
    order: DraftOrder
    action: str
    action_result: OrderActionResult
    current_step: str
    tool_error: dict[str, Any]
    audit_events: list[dict[str, Any]]
    response: BookingResponse
