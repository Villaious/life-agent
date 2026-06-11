import pytest

from app.agents.booking_agent import BookingAgent
from app.memory.checkpoint import SessionCheckpointStore
from app.models.booking import BookingRequest, BookingStatus


@pytest.mark.asyncio
async def test_session_checkpoint_recovers_missing_context() -> None:
    store = SessionCheckpointStore(backend="memory")
    agent = BookingAgent(checkpoint_store=store)

    first = await agent.run(
        "帮我预约保洁",
        request=BookingRequest(
            user_id="user_checkpoint",
            session_id="session_checkpoint",
            message="帮我预约保洁",
            context={"location": "深圳南山"},
        ),
    )
    assert first.status == BookingStatus.NEEDS_INFO

    second = await agent.run(
        "明天下午",
        request=BookingRequest(
            user_id="user_checkpoint",
            session_id="session_checkpoint",
            message="帮我预约保洁",
            context={"time_preference": "明天下午"},
        ),
    )
    assert second.status == BookingStatus.CREATED


@pytest.mark.parametrize("action", ["payment", "reschedule", "cancel", "review"])
@pytest.mark.asyncio
async def test_order_action_nodes(action: str) -> None:
    response = await BookingAgent().run(
        action,
        request=BookingRequest(
            user_id="user_001",
            message=action,
            context={
                "action": action,
                "task_id": "task_existing_001",
                "payment_method": "mock_pay",
                "new_time_preference": "后天下午",
                "reason": "计划变更",
                "rating": 5,
                "comment": "服务很好",
            },
        ),
    )

    assert response.status == BookingStatus.COMPLETED
    assert response.action_result is not None
    assert response.action_result.action == action
