import pytest

from app.integrations.local_life_client import LocalLifeServiceClient


@pytest.mark.asyncio
async def test_local_life_client_dry_run_match_services() -> None:
    client = LocalLifeServiceClient(dry_run=True)

    candidates = await client.match_services(
        {"service_category": "home_cleaning", "location": "深圳南山"}
    )

    assert candidates[0].category == "home_cleaning"
    assert candidates[0].location == "深圳南山"
    assert candidates[0].price.amount == 168
    assert candidates[0].fulfillment.duration_minutes == 120
    assert candidates[0].inventory_lock.locked is True


@pytest.mark.asyncio
async def test_local_life_client_dry_run_confirm_slot() -> None:
    client = LocalLifeServiceClient(dry_run=True)

    slot = await client.confirm_slot({"time_preference": "明天下午"})

    assert slot.start_time == "明天下午"
    assert slot.confirmation_required is True
    assert slot.inventory_lock.locked is True


@pytest.mark.asyncio
async def test_local_life_client_dry_run_create_order_draft() -> None:
    client = LocalLifeServiceClient(dry_run=True)

    order = await client.create_order_draft(
        {
            "slot": {"start_time": "明天下午"},
            "provider": {"provider_id": "provider_001"},
        }
    )

    assert order.task_id.startswith("task_")
    assert order.status == "draft"


@pytest.mark.asyncio
async def test_local_life_client_normalizes_provider_fields() -> None:
    client = LocalLifeServiceClient(dry_run=False, base_url="https://example.test")

    async def fake_post(path: str, payload: dict):
        return {
            "candidates": [
                {
                    "id": "provider_001",
                    "provider_name": "安心到家保洁",
                    "category": "home_cleaning",
                    "price_amount": 199,
                    "currency": "CNY",
                    "price_unit": "次",
                    "city": "深圳",
                    "district": "南山",
                    "duration_minutes": 150,
                    "service_mode": "on_site",
                    "inventory_lock_id": "lock_001",
                    "inventory_locked": True,
                    "lock_expires_at": "2026-06-08T14:00:00+08:00",
                }
            ]
        }

    client._post = fake_post
    candidates = await client.match_services({"service_category": "home_cleaning"})

    candidate = candidates[0]
    assert candidate.provider_id == "provider_001"
    assert candidate.name == "安心到家保洁"
    assert candidate.price.amount == 199
    assert candidate.service_area.district == "南山"
    assert candidate.fulfillment.duration_minutes == 150
    assert candidate.inventory_lock.lock_id == "lock_001"
