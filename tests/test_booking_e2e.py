import httpx
import pytest

from app.agents.booking_agent import BookingAgent
from app.integrations.local_life_client import LocalLifeServiceClient
from app.models.booking import BookingRequest, BookingStatus
from app.tools.builtin.booking_tools import OrderDraftTool, ServiceMatchTool, SlotConfirmTool


@pytest.mark.asyncio
async def test_e2e_multi_turn_booking_recovery() -> None:
    first_response = await BookingAgent().run(
        "帮我预约保洁",
        request=BookingRequest(user_id="user_001", message="帮我预约保洁"),
    )
    assert first_response.status == BookingStatus.NEEDS_INFO

    second_response = await BookingAgent().run(
        "帮我预约保洁",
        request=BookingRequest(
            user_id="user_001",
            message="帮我预约保洁",
            session_id="session_001",
            context={"location": "深圳南山", "time_preference": "明天下午"},
        ),
    )
    assert second_response.status == BookingStatus.CREATED
    assert second_response.task_id is not None


class InvalidJsonLLM:
    @property
    def is_live(self) -> bool:
        return True

    async def complete(self, prompt: str, system_prompt: str | None = None) -> str:
        return "这不是 JSON"


@pytest.mark.asyncio
async def test_e2e_llm_parse_failure_falls_back_to_rules() -> None:
    agent = BookingAgent()
    agent.llm = InvalidJsonLLM()

    response = await agent.run(
        "帮我预约保洁",
        request=BookingRequest(
            user_id="user_001",
            message="帮我预约保洁",
            context={"location": "深圳南山", "time_preference": "明天下午"},
        ),
    )

    assert response.status == BookingStatus.CREATED
    assert len(response.candidates) > 0
    # 高德地图返回真实的中文分类名（如"保洁"、"家政服务"、"搬家"等）
    assert response.candidates[0].category in {
        "保洁", "家政服务", "搬家", "管道疏通",
        "家电维修", "保姆月嫂", "其他家政服务",
    }


@pytest.mark.asyncio
async def test_e2e_local_life_api_timeout_returns_failed() -> None:
    client = LocalLifeServiceClient(dry_run=False, base_url="https://example.test")

    async def timeout_post(path: str, payload: dict):
        raise httpx.TimeoutException("upstream timeout")

    client._post = timeout_post
    agent = BookingAgent(
        tools=[ServiceMatchTool(client), SlotConfirmTool(client), OrderDraftTool(client)]
    )

    response = await agent.run(
        "帮我预约保洁",
        request=BookingRequest(
            user_id="user_001",
            message="帮我预约保洁",
            context={"location": "深圳南山", "time_preference": "明天下午"},
        ),
    )

    assert response.status == BookingStatus.FAILED
    assert "暂时不可用" in response.reply


@pytest.mark.asyncio
async def test_e2e_permission_denied_for_order_write() -> None:
    response = await BookingAgent().run(
        "帮我预约保洁",
        request=BookingRequest(
            user_id="user_001",
            message="帮我预约保洁",
            context={
                "location": "深圳南山",
                "time_preference": "明天下午",
                "permissions": [
                    "booking:match",
                    "booking:slot",
                    "booking:order",
                    "external_api:local_life",
                    "privacy:user_context",
                ],
            },
        ),
    )

    assert response.status == BookingStatus.FAILED
    assert "权限" in response.reply
