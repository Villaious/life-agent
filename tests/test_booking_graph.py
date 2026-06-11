import pytest

from app.agents.booking_agent import BookingAgent
from app.agents.booking_graph import run_booking_graph
from app.models.booking import BookingRequest, BookingStatus
from app.tools.base import BaseTool, ToolResult
from app.tools.builtin.booking_tools import OrderDraftTool, SlotConfirmTool


@pytest.mark.asyncio
async def test_booking_graph_asks_for_missing_fields() -> None:
    response = await run_booking_graph(
        BookingRequest(user_id="user_001", message="帮我预约保洁")
    )

    assert response.status == BookingStatus.NEEDS_INFO
    assert "location" in response.missing_fields
    assert "time_preference" in response.missing_fields


@pytest.mark.asyncio
async def test_booking_graph_creates_draft_order() -> None:
    response = await run_booking_graph(
        BookingRequest(
            user_id="user_001",
            message="帮我预约保洁",
            context={"location": "深圳南山科技园科兴科学园", "time_preference": "明天下午"},
        )
    )

    assert response.status == BookingStatus.CREATED
    assert response.task_id is not None


class FailingServiceMatchTool(BaseTool):
    name = "service_match"
    description = "Failing service match tool for tests."
    permission = "booking:match"

    async def arun(self, payload: dict) -> ToolResult:
        return ToolResult(ok=False, error="upstream_unavailable")


@pytest.mark.asyncio
async def test_booking_graph_handles_tool_failure() -> None:
    agent = BookingAgent(
        tools=[FailingServiceMatchTool(), SlotConfirmTool(), OrderDraftTool()]
    )

    response = await agent.run(
        "帮我预约保洁",
        request=BookingRequest(
            user_id="user_001",
            message="帮我预约保洁",
            context={"location": "深圳南山科技园科兴科学园", "time_preference": "明天下午"},
        ),
    )

    assert response.status == BookingStatus.FAILED
    assert "暂时不可用" in response.reply


@pytest.mark.asyncio
async def test_booking_graph_rejects_missing_tool_permission() -> None:
    response = await run_booking_graph(
        BookingRequest(
            user_id="user_001",
            message="帮我预约保洁",
            context={
                "location": "深圳南山科技园科兴科学园",
                "time_preference": "明天下午",
                "permissions": ["booking:match", "booking:slot"],
            },
        )
    )

    assert response.status == BookingStatus.FAILED
    assert "权限" in response.reply
