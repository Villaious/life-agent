from typing import Any

from sqlalchemy import select
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
    session_id: str | None,
    order: Any,
) -> BookingOrderRecord:
    payload = order.model_dump(mode="json") if hasattr(order, "model_dump") else dict(order)
    provider = payload.get("provider") or {}
    record = BookingOrderRecord(
        task_id=payload["task_id"],
        user_id=user_id,
        session_id=session_id,
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


async def save_order_action_result(
    session: AsyncSession,
    user_id: str,
    session_id: str | None,
    action_result: Any,
) -> BookingOrderRecord:
    payload = (
        action_result.model_dump(mode="json")
        if hasattr(action_result, "model_dump")
        else dict(action_result)
    )
    task_id = payload["task_id"]
    statement = (
        select(BookingOrderRecord)
        .where(
            BookingOrderRecord.user_id == user_id,
            BookingOrderRecord.task_id == task_id,
        )
        .order_by(BookingOrderRecord.created_at.desc())
        .limit(1)
    )
    result = await session.execute(statement)
    record = result.scalar_one_or_none()

    if record is None:
        record = BookingOrderRecord(
            task_id=task_id,
            user_id=user_id,
            session_id=session_id,
            provider_id=None,
            status=payload.get("status", "action_accepted"),
            price=None,
            slot=None,
            provider=None,
            inventory_lock=None,
            raw_payload={"last_action": payload, "action_history": [payload]},
        )
        session.add(record)
        await session.flush()
        return record

    raw_payload = dict(record.raw_payload or {})
    history = list(raw_payload.get("action_history") or [])
    history.append(payload)
    raw_payload["last_action"] = payload
    raw_payload["action_history"] = history
    record.session_id = record.session_id or session_id
    record.status = payload.get("status", record.status)
    record.raw_payload = raw_payload
    await session.flush()
    return record


async def list_booking_orders(
    session: AsyncSession,
    user_id: str,
    session_id: str | None = None,
    task_id: str | None = None,
    limit: int = 20,
) -> list[BookingOrderRecord]:
    statement = select(BookingOrderRecord).where(BookingOrderRecord.user_id == user_id)
    if session_id:
        statement = statement.where(BookingOrderRecord.session_id == session_id)
    if task_id:
        statement = statement.where(BookingOrderRecord.task_id == task_id)
    statement = statement.order_by(BookingOrderRecord.created_at.desc()).limit(limit)
    result = await session.execute(statement)
    return list(result.scalars().all())


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
