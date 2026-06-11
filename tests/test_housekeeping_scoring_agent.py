import pytest

from app.agents.booking_agent import BookingAgent
from app.agents.housekeeping_scoring_agent import HousekeepingScoringAgent
from app.models.booking import BookingRequest, BookingStatus, PriceInfo, ServiceCandidate
from app.tools.base import BaseTool, ToolResult
from app.tools.builtin.booking_tools import OrderDraftTool, SlotConfirmTool


def test_housekeeping_scorer_filters_unrelated_services_and_sorts_best() -> None:
    candidates = [
        ServiceCandidate(
            provider_id="moving_001",
            name="安心搬家公司",
            category="搬家",
            price=PriceInfo(amount=80),
            raw={"distance": "300"},
        ),
        ServiceCandidate(
            provider_id="cleaning_far",
            name="远距离保洁",
            category="保洁",
            price=PriceInfo(amount=180),
            raw={"distance": "4500"},
        ),
        ServiceCandidate(
            provider_id="cleaning_best",
            name="近距离保洁",
            category="保洁",
            price=PriceInfo(amount=120),
            raw={"distance": "400"},
        ),
    ]

    selected = HousekeepingScoringAgent().select_best(candidates, "home_cleaning")

    assert [candidate.provider_id for candidate in selected] == ["cleaning_best", "cleaning_far"]
    assert selected[0].expected_score is not None
    assert selected[0].expected_score > selected[1].expected_score


class MixedServiceMatchTool(BaseTool):
    name = "service_match"
    description = "Return mixed service candidates."
    permission = "booking:match"

    async def arun(self, payload: dict) -> ToolResult:
        return ToolResult(
            data={
                "candidates": [
                    ServiceCandidate(
                        provider_id="moving_001",
                        name="安心搬家公司",
                        category="搬家",
                        price=PriceInfo(amount=50),
                        raw={"distance": "200"},
                    ),
                    ServiceCandidate(
                        provider_id="cleaning_best",
                        name="近距离保洁",
                        category="保洁",
                        price=PriceInfo(amount=120),
                        raw={"distance": "400"},
                    ),
                ]
            }
        )


@pytest.mark.asyncio
async def test_booking_agent_rejects_imprecise_address() -> None:
    response = await BookingAgent().run(
        "帮我预约明天下午山西太原的上门保洁",
        request=BookingRequest(
            user_id="user_001",
            message="帮我预约明天下午山西太原的上门保洁",
        ),
    )

    assert response.status == BookingStatus.NEEDS_INFO
    assert "address_detail" in response.missing_fields


@pytest.mark.asyncio
async def test_booking_agent_selects_highest_scored_cleaning_provider() -> None:
    agent = BookingAgent(
        tools=[MixedServiceMatchTool(), SlotConfirmTool(), OrderDraftTool()],
    )

    response = await agent.run(
        "帮我预约明天下午太原科技大学的上门保洁",
        request=BookingRequest(
            user_id="user_001",
            message="帮我预约明天下午太原科技大学的上门保洁",
        ),
    )

    assert response.status == BookingStatus.CREATED
    assert [candidate.provider_id for candidate in response.candidates] == ["cleaning_best"]
    assert response.candidates[0].expected_score is not None
