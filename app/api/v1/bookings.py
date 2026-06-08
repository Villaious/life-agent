from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.booking_graph import run_booking_graph
from app.db.repositories import list_booking_orders
from app.db.session import get_session
from app.models.booking import (
    BookingOrderQueryResponse,
    BookingOrderView,
    BookingRequest,
    BookingResponse,
)

router = APIRouter()


@router.post("", response_model=BookingResponse)
async def create_booking(request: BookingRequest) -> BookingResponse:
    return await run_booking_graph(request)


@router.get("/orders", response_model=BookingOrderQueryResponse)
async def query_booking_orders(
    user_id: str = Query(..., min_length=1),
    session_id: str | None = Query(default=None),
    task_id: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
) -> BookingOrderQueryResponse:
    try:
        orders = await list_booking_orders(
            session=session,
            user_id=user_id,
            session_id=session_id,
            task_id=task_id,
            limit=limit,
        )
    except Exception as exc:
        raise HTTPException(status_code=503, detail="订单数据库暂不可用，请先启动 PostgreSQL。") from exc

    return BookingOrderQueryResponse(
        orders=[
            BookingOrderView(
                task_id=order.task_id,
                user_id=order.user_id,
                session_id=order.session_id,
                status=order.status,
                provider_id=order.provider_id,
                price=order.price,
                slot=order.slot,
                provider=order.provider,
                inventory_lock=order.inventory_lock,
                raw_payload=order.raw_payload,
                created_at=order.created_at,
                updated_at=order.updated_at,
            )
            for order in orders
        ]
    )
