from enum import StrEnum
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class BookingStatus(StrEnum):
    NEEDS_INFO = "needs_info"
    MATCHING = "matching"
    WAITING_CONFIRMATION = "waiting_confirmation"
    CREATED = "created"
    FAILED = "failed"
    COMPLETED = "completed"


class BookingRequest(BaseModel):
    user_id: str = Field(..., examples=["user_001"])
    message: str = Field(..., examples=["帮我明天下午约一个上门保洁"])
    session_id: str | None = None
    context: dict[str, Any] = Field(default_factory=dict)


class PriceInfo(BaseModel):
    amount: float | None = None
    currency: str = "CNY"
    unit: str | None = None
    display_text: str | None = None


class ServiceArea(BaseModel):
    city: str | None = None
    district: str | None = None
    address_hint: str | None = None
    radius_km: float | None = None


class FulfillmentInfo(BaseModel):
    duration_minutes: int | None = None
    service_mode: str | None = None
    earliest_start_time: str | None = None


class InventoryLock(BaseModel):
    lock_id: str | None = None
    locked: bool = False
    expires_at: str | None = None
    status: str | None = None


class ServiceCandidate(BaseModel):
    provider_id: str
    name: str
    category: str = "unknown"
    location: str | None = None
    phone: str | None = None
    score: float | None = None
    expected_score: float | None = None
    score_explanation: str | None = None
    price: PriceInfo = Field(default_factory=PriceInfo)
    service_area: ServiceArea = Field(default_factory=ServiceArea)
    fulfillment: FulfillmentInfo = Field(default_factory=FulfillmentInfo)
    inventory_lock: InventoryLock = Field(default_factory=InventoryLock)
    raw: dict[str, Any] = Field(default_factory=dict)


class AppointmentSlot(BaseModel):
    start_time: str | None = None
    end_time: str | None = None
    timezone: str = "Asia/Hong_Kong"
    confirmation_required: bool = True
    inventory_lock: InventoryLock = Field(default_factory=InventoryLock)
    raw: dict[str, Any] = Field(default_factory=dict)


class DraftOrder(BaseModel):
    task_id: str
    status: str = "draft"
    provider: dict[str, Any] | None = None
    slot: dict[str, Any] | None = None
    price: PriceInfo = Field(default_factory=PriceInfo)
    inventory_lock: InventoryLock = Field(default_factory=InventoryLock)
    raw: dict[str, Any] = Field(default_factory=dict)


class OrderActionResult(BaseModel):
    action: str
    task_id: str
    status: str
    raw: dict[str, Any] = Field(default_factory=dict)


class BookingResponse(BaseModel):
    status: BookingStatus
    reply: str
    task_id: str | None = None
    parsed_intent: dict[str, Any] | None = None
    missing_fields: list[str] = Field(default_factory=list)
    candidates: list[ServiceCandidate] = Field(default_factory=list)
    action_result: OrderActionResult | None = None


class BookingOrderView(BaseModel):
    task_id: str
    user_id: str
    session_id: str | None = None
    status: str
    provider_id: str | None = None
    price: dict[str, Any] | None = None
    slot: dict[str, Any] | None = None
    provider: dict[str, Any] | None = None
    inventory_lock: dict[str, Any] | None = None
    raw_payload: dict[str, Any] | None = None
    created_at: datetime
    updated_at: datetime


class BookingOrderQueryResponse(BaseModel):
    orders: list[BookingOrderView] = Field(default_factory=list)
