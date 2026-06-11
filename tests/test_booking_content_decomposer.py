from datetime import datetime, timedelta, timezone

import pytest

from app.agents.booking_agent import BookingAgent
from app.agents.booking_content_decomposer import BookingContentDecomposerAgent
from app.memory.checkpoint import SessionCheckpointStore
from app.models.booking import BookingRequest, BookingStatus
from app.services.persistence import BookingPersistenceService


def fixed_now() -> datetime:
    return datetime(2026, 6, 11, 10, 0, tzinfo=timezone(timedelta(hours=8)))


def test_decomposer_extracts_event_location_and_relative_time() -> None:
    agent = BookingContentDecomposerAgent()

    intent = agent.decompose("帮我预约明天下午深圳南山的上门保洁", now=fixed_now())

    assert intent["event"] == "上门保洁"
    assert intent["service_category"] == "home_cleaning"
    assert intent["location"] == "深圳南山"
    assert intent["time_preference"] == "2026-06-12 下午"


def test_decomposer_uses_today_for_day_part_without_date() -> None:
    agent = BookingContentDecomposerAgent()

    intent = agent.decompose("今天下午在深圳福田预约保洁", now=fixed_now())

    assert intent["location"] == "深圳福田"
    assert intent["time_preference"] == "2026-06-11 下午"


def test_decomposer_extracts_cold_province_city_location() -> None:
    agent = BookingContentDecomposerAgent()

    intent = agent.decompose("帮我预约明天下午山西太原的上门保洁", now=fixed_now())

    assert intent["location"] == "山西太原"
    assert intent["time_preference"] == "2026-06-12 下午"


def test_decomposer_extracts_university_location() -> None:
    agent = BookingContentDecomposerAgent()

    intent = agent.decompose("帮我预约明天下午太原科技大学的上门保洁", now=fixed_now())

    assert intent["location"] == "太原科技大学"
    assert intent["time_preference"] == "2026-06-12 下午"


@pytest.mark.asyncio
async def test_booking_agent_uses_decomposer_without_context_fields() -> None:
    agent = BookingAgent(
        persistence=BookingPersistenceService(enabled=False),
        checkpoint_store=SessionCheckpointStore(backend="memory"),
    )

    response = await agent.run(
        "帮我预约明天下午深圳南山的上门保洁",
        request=BookingRequest(user_id="user_001", message="帮我预约明天下午深圳南山的上门保洁"),
    )

    assert response.status == BookingStatus.CREATED
    assert response.task_id is not None
    assert response.parsed_intent is not None
    assert response.parsed_intent["event"] == "上门保洁"
    assert response.parsed_intent["location"] == "深圳南山"
    assert response.parsed_intent["time_preference"]
