import os

import pytest

from app.integrations.local_life_client import LocalLifeServiceClient


pytestmark = pytest.mark.contract


def _sandbox_enabled() -> bool:
    return bool(os.getenv("LOCAL_LIFE_SANDBOX_BASE_URL"))


@pytest.mark.skipif(not _sandbox_enabled(), reason="LOCAL_LIFE_SANDBOX_BASE_URL is not set")
@pytest.mark.asyncio
async def test_contract_match_services() -> None:
    client = LocalLifeServiceClient.sandbox()

    candidates = await client.match_services(
        {"service_category": "home_cleaning", "location": "深圳南山"}
    )

    assert candidates
    assert candidates[0].provider_id
    assert candidates[0].price.currency


@pytest.mark.skipif(not _sandbox_enabled(), reason="LOCAL_LIFE_SANDBOX_BASE_URL is not set")
@pytest.mark.asyncio
async def test_contract_confirm_slot_and_order_draft() -> None:
    client = LocalLifeServiceClient.sandbox()
    candidates = await client.match_services(
        {"service_category": "home_cleaning", "location": "深圳南山"}
    )
    slot = await client.confirm_slot(
        {
            "raw_text": "帮我预约保洁",
            "service_category": "home_cleaning",
            "location": "深圳南山",
            "time_preference": "明天下午",
        }
    )
    order = await client.create_order_draft(
        {"provider": candidates[0], "slot": slot}
    )

    assert slot.timezone
    assert order.task_id
