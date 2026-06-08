from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import BookingOrderRecord, BookingTaskRecord, ToolAuditLogRecord
from app.models.booking import BookingRequest, BookingResponse
from app.models.state import BookingGraphState
from app.tools.policy import ToolContext


async def save_booking_task(
    session: AsyncSession,
    state: BookingGraphState,
    response: BookingResponse,
) -> BookingTaskRecord:
    request = state["request"]
    record = BookingTaskRecord(
        task_id=response.task_id,
        user_id=request.user_id,
        session_id=request.session_id,
        status=response.status,
        current_step=state.get("current_step"),
        request_payload=request.model_dump(),
        intent=state.get("intent"),
        missing_fields=state.get("missing_fields", []),
        response_payload=response.model_dump(mode="json"),
    )
    session.add(record)
    await session.flush()
    return record


async def save_booking_order(
    session: AsyncSession,
    user_id: str,
    order: Any,
) -> BookingOrderRecord:
    payload = order.model_dump(mode="json") if hasattr(order, "model_dump") else dict(order)
    provider = payload.get("provider") or {}
    record = BookingOrderRecord(
        task_id=payload["task_id"],
        user_id=user_id,
        provider_id=provider.get("provider_id"),
        status=payload.get("status", "draft"),
        price=payload.get("price"),
        slot=payload.get("slot"),
        provider=provider,
        inventory_lock=payload.get("inventory_lock"),
        raw_payload=payload.get("raw"),
    )
    session.add(record)
    await session.flush()
    return record


async def save_tool_audit_log(
    session: AsyncSession,
    context: ToolContext,
    event: dict[str, Any],
) -> ToolAuditLogRecord:
    record = ToolAuditLogRecord(
        task_id=context.task_id,
        user_id=context.user_id,
        step=event.get("step"),
        tool=event.get("tool", "unknown"),
        status=event.get("status", "unknown"),
        permissions=sorted(context.permissions),
        privacy_scopes=sorted(context.privacy_scopes or []),
        request_payload=event.get("request_payload"),
        response_payload=event.get("response_payload"),
        error=event.get("error"),
    )
    session.add(record)
    await session.flush()
    return record
