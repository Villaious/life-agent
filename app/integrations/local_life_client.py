from typing import Any
from uuid import uuid4

import httpx

from app.core.config import settings
from app.models.booking import (
    AppointmentSlot,
    DraftOrder,
    FulfillmentInfo,
    InventoryLock,
    PriceInfo,
    OrderActionResult,
    ServiceArea,
    ServiceCandidate,
)


class LocalLifeServiceClient:
    def __init__(
        self,
        base_url: str | None = None,
        api_key: str | None = None,
        timeout: float | None = None,
        dry_run: bool | None = None,
    ) -> None:
        self.base_url = (base_url if base_url is not None else settings.local_life_api_base_url).rstrip("/")
        self.api_key = api_key if api_key is not None else settings.local_life_api_key
        self.timeout = timeout if timeout is not None else settings.local_life_timeout
        self.dry_run = settings.local_life_dry_run if dry_run is None else dry_run

    @classmethod
    def sandbox(cls) -> "LocalLifeServiceClient":
        return cls(
            base_url=settings.local_life_sandbox_base_url,
            api_key=settings.local_life_sandbox_api_key,
            dry_run=False,
        )

    async def match_services(self, payload: dict[str, Any]) -> list[ServiceCandidate]:
        if self._should_dry_run:
            return [
                ServiceCandidate(
                    provider_id="dry_run_provider_001",
                    name="开发模式服务商",
                    category=payload.get("service_category", "unknown"),
                    location=payload.get("location"),
                    phone="0755-88886666",
                    score=0.82,
                    price=PriceInfo(amount=168, currency="CNY", unit="次", display_text="¥168/次"),
                    service_area=ServiceArea(city="深圳", district="南山", address_hint=payload.get("location")),
                    fulfillment=FulfillmentInfo(duration_minutes=120, service_mode="on_site"),
                    inventory_lock=InventoryLock(
                        lock_id="dry_run_lock_service",
                        locked=True,
                        status="locked",
                    ),
                )
            ]

        data = await self._post("/services/match", payload)
        candidates = data.get("candidates", data if isinstance(data, list) else [])
        if not isinstance(candidates, list):
            raise ValueError("Local life API returned invalid candidates.")
        return [self._normalize_candidate(candidate) for candidate in candidates]

    async def confirm_slot(self, payload: dict[str, Any]) -> AppointmentSlot:
        if self._should_dry_run:
            return AppointmentSlot(
                start_time=payload.get("time_preference"),
                timezone="Asia/Hong_Kong",
                confirmation_required=True,
                inventory_lock=InventoryLock(
                    lock_id="dry_run_lock_slot",
                    locked=True,
                    status="locked",
                ),
                raw={"source": "dry_run"},
            )

        data = await self._post("/availability/confirm", payload)
        slot = data.get("slot", data)
        if not isinstance(slot, dict):
            raise ValueError("Local life API returned invalid slot.")
        return self._normalize_slot(slot)

    async def create_order_draft(self, payload: dict[str, Any]) -> DraftOrder:
        if self._should_dry_run:
            provider = self._dump_model(payload.get("provider"))
            slot = self._dump_model(payload.get("slot"))
            return DraftOrder(
                task_id=f"task_{uuid4().hex[:12]}",
                status="draft",
                slot=slot,
                provider=provider,
                price=PriceInfo(amount=provider.get("price", {}).get("amount") if provider else None),
                inventory_lock=InventoryLock(
                    lock_id="dry_run_lock_order",
                    locked=True,
                    status="locked",
                ),
                raw={"source": "dry_run"},
            )

        data = await self._post("/orders/drafts", payload)
        order = data.get("order", data)
        if not isinstance(order, dict):
            raise ValueError("Local life API returned invalid order.")
        return self._normalize_order(order)

    async def create_payment(self, payload: dict[str, Any]) -> OrderActionResult:
        return await self._order_action("payment", "/orders/payments", payload)

    async def reschedule_order(self, payload: dict[str, Any]) -> OrderActionResult:
        return await self._order_action("reschedule", "/orders/reschedule", payload)

    async def cancel_order(self, payload: dict[str, Any]) -> OrderActionResult:
        return await self._order_action("cancel", "/orders/cancel", payload)

    async def review_order(self, payload: dict[str, Any]) -> OrderActionResult:
        return await self._order_action("review", "/orders/reviews", payload)

    @property
    def _should_dry_run(self) -> bool:
        return self.dry_run or not self.base_url

    async def _post(self, path: str, payload: dict[str, Any]) -> Any:
        headers = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.base_url}{path}",
                json=self._jsonable(payload),
                headers=headers,
            )
            response.raise_for_status()
            return response.json()

    def _normalize_candidate(self, raw: dict[str, Any]) -> ServiceCandidate:
        price_raw = raw.get("price", {})
        area_raw = raw.get("service_area", raw.get("area", {}))
        fulfillment_raw = raw.get("fulfillment", raw.get("fulfillment_info", {}))
        lock_raw = raw.get("inventory_lock", raw.get("lock", {}))
        return ServiceCandidate(
            provider_id=str(raw.get("provider_id") or raw.get("id")),
            name=str(raw.get("name") or raw.get("provider_name")),
            category=str(raw.get("category", "unknown")),
            location=raw.get("location"),
            phone=raw.get("phone")
            or raw.get("tel")
            or raw.get("telephone")
            or raw.get("provider_phone")
            or raw.get("contact_phone"),
            score=raw.get("score"),
            price=PriceInfo(
                amount=price_raw.get("amount") or raw.get("price_amount"),
                currency=price_raw.get("currency", raw.get("currency", "CNY")),
                unit=price_raw.get("unit") or raw.get("price_unit"),
                display_text=price_raw.get("display_text") or raw.get("price_text"),
            ),
            service_area=ServiceArea(
                city=area_raw.get("city") or raw.get("city"),
                district=area_raw.get("district") or raw.get("district"),
                address_hint=area_raw.get("address_hint") or raw.get("address_hint"),
                radius_km=area_raw.get("radius_km") or raw.get("service_radius_km"),
            ),
            fulfillment=FulfillmentInfo(
                duration_minutes=fulfillment_raw.get("duration_minutes")
                or raw.get("duration_minutes"),
                service_mode=fulfillment_raw.get("service_mode") or raw.get("service_mode"),
                earliest_start_time=fulfillment_raw.get("earliest_start_time")
                or raw.get("earliest_start_time"),
            ),
            inventory_lock=InventoryLock(
                lock_id=lock_raw.get("lock_id") or raw.get("inventory_lock_id"),
                locked=bool(lock_raw.get("locked", raw.get("inventory_locked", False))),
                expires_at=lock_raw.get("expires_at") or raw.get("lock_expires_at"),
                status=lock_raw.get("status") or raw.get("inventory_status"),
            ),
            raw=raw,
        )

    def _normalize_slot(self, raw: dict[str, Any]) -> AppointmentSlot:
        lock_raw = raw.get("inventory_lock", raw.get("lock", {}))
        return AppointmentSlot(
            start_time=raw.get("start_time"),
            end_time=raw.get("end_time"),
            timezone=raw.get("timezone", "Asia/Hong_Kong"),
            confirmation_required=bool(raw.get("confirmation_required", True)),
            inventory_lock=InventoryLock(
                lock_id=lock_raw.get("lock_id") or raw.get("inventory_lock_id"),
                locked=bool(lock_raw.get("locked", raw.get("inventory_locked", False))),
                expires_at=lock_raw.get("expires_at") or raw.get("lock_expires_at"),
                status=lock_raw.get("status") or raw.get("inventory_status"),
            ),
            raw=raw,
        )

    def _normalize_order(self, raw: dict[str, Any]) -> DraftOrder:
        lock_raw = raw.get("inventory_lock", raw.get("lock", {}))
        return DraftOrder(
            task_id=str(raw.get("task_id") or raw.get("order_id")),
            status=raw.get("status", "draft"),
            provider=raw.get("provider"),
            slot=raw.get("slot"),
            price=PriceInfo(**raw.get("price", {})) if isinstance(raw.get("price"), dict) else PriceInfo(),
            inventory_lock=InventoryLock(
                lock_id=lock_raw.get("lock_id") or raw.get("inventory_lock_id"),
                locked=bool(lock_raw.get("locked", raw.get("inventory_locked", False))),
                expires_at=lock_raw.get("expires_at") or raw.get("lock_expires_at"),
                status=lock_raw.get("status") or raw.get("inventory_status"),
            ),
            raw=raw,
        )

    async def _order_action(
        self,
        action: str,
        path: str,
        payload: dict[str, Any],
    ) -> OrderActionResult:
        task_id = str(payload.get("task_id") or payload.get("order_id") or "")
        if self._should_dry_run:
            return OrderActionResult(
                action=action,
                task_id=task_id or f"task_{uuid4().hex[:12]}",
                status=f"{action}_accepted",
                raw={"source": "dry_run", **payload},
            )

        data = await self._post(path, payload)
        result = data.get("result", data)
        return OrderActionResult(
            action=action,
            task_id=str(result.get("task_id") or result.get("order_id") or task_id),
            status=str(result.get("status") or f"{action}_accepted"),
            raw=result,
        )

    def _dump_model(self, value: Any) -> dict[str, Any] | None:
        if value is None:
            return None
        if hasattr(value, "model_dump"):
            return value.model_dump()
        if isinstance(value, dict):
            return value
        return {"value": value}

    def _jsonable(self, value: Any) -> Any:
        if hasattr(value, "model_dump"):
            return value.model_dump(mode="json")
        if isinstance(value, list):
            return [self._jsonable(item) for item in value]
        if isinstance(value, dict):
            return {key: self._jsonable(item) for key, item in value.items()}
        return value
