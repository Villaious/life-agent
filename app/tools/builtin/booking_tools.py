import logging
from typing import Any

from app.integrations.amap_client import AmapClient
from app.integrations.local_life_client import LocalLifeServiceClient
from app.tools.base import BaseTool, ToolResult

logger = logging.getLogger(__name__)


class ServiceMatchTool(BaseTool):
    name = "service_match"
    description = "通过高德地图搜索目标地点附近的家政保洁等服务商。"
    permission = "booking:match"
    required_permissions = {"booking:match", "external_api:local_life", "privacy:user_context"}

    def __init__(
        self,
        client: LocalLifeServiceClient | None = None,
        amap_client: AmapClient | None = None,
    ) -> None:
        self.client = client or LocalLifeServiceClient()
        self.amap = amap_client or AmapClient()

    async def arun(self, payload: dict[str, Any]) -> ToolResult:
        location = payload.get("location", "")
        if not location:
            return ToolResult(ok=False, error="缺少目标位置信息")

        try:
            # 优先使用高德地图 API 搜索附近服务
            if self.amap.api_key:
                candidates = await self._search_via_amap(payload)
            else:
                # 回退到原有 LocalLifeServiceClient
                logger.info("AMAP_API_KEY 未配置，使用 LocalLifeServiceClient 回退")
                candidates = await self.client.match_services(payload)
        except Exception as exc:
            logger.error("ServiceMatchTool 执行失败: %s", exc, exc_info=True)
            return ToolResult(ok=False, error=str(exc))

        return ToolResult(data={"candidates": candidates})

    async def _search_via_amap(self, payload: dict[str, Any]) -> list[Any]:
        """使用高德地图搜索附近的家政保洁服务。"""
        location = payload.get("location", "")

        # 判断是否为坐标格式
        if _is_coordinate(location):
            candidates = await self.amap.search_housekeeping_services(
                location=location,
            )
        else:
            # 将地址解析为坐标后再搜索
            city = payload.get("city") or _extract_city(location)
            _, candidates = await self.amap.search_services_by_address(
                address=location,
                city=city,
            )

        return candidates


def _is_coordinate(value: str) -> bool:
    """判断字符串是否为经纬度坐标格式（如 "116.397428,39.90923"）。"""
    value = value.strip()
    parts = value.split(",")
    if len(parts) != 2:
        return False
    try:
        float(parts[0])
        float(parts[1])
        return True
    except ValueError:
        return False


def _extract_city(address: str) -> str | None:
    """从地址中尝试提取城市名。"""
    if "市" in address[:3]:
        idx = address.index("市")
        return address[: idx + 1]
    return None


class SlotConfirmTool(BaseTool):
    name = "slot_confirm"
    description = "Create a candidate appointment slot from user preference."
    permission = "booking:slot"
    required_permissions = {"booking:slot", "external_api:local_life", "privacy:user_context"}

    def __init__(self, client: LocalLifeServiceClient | None = None) -> None:
        self.client = client or LocalLifeServiceClient()

    async def arun(self, payload: dict[str, Any]) -> ToolResult:
        try:
            slot = await self.client.confirm_slot(payload)
        except Exception as exc:
            return ToolResult(ok=False, error=str(exc))
        return ToolResult(data={"slot": slot})


class OrderDraftTool(BaseTool):
    name = "order_draft"
    description = "Create a draft booking order."
    permission = "booking:order"
    required_permissions = {"booking:order", "external_api:local_life", "order:write"}

    def __init__(self, client: LocalLifeServiceClient | None = None) -> None:
        self.client = client or LocalLifeServiceClient()

    async def arun(self, payload: dict[str, Any]) -> ToolResult:
        try:
            order = await self.client.create_order_draft(payload)
        except Exception as exc:
            return ToolResult(ok=False, error=str(exc))
        return ToolResult(data={"order": order})


class PaymentTool(BaseTool):
    name = "payment_create"
    description = "Create a payment request for a booking order."
    permission = "payment:write"
    required_permissions = {"payment:write", "external_api:local_life", "order:read"}

    def __init__(self, client: LocalLifeServiceClient | None = None) -> None:
        self.client = client or LocalLifeServiceClient()

    async def arun(self, payload: dict[str, Any]) -> ToolResult:
        try:
            result = await self.client.create_payment(payload)
        except Exception as exc:
            return ToolResult(ok=False, error=str(exc))
        return ToolResult(data={"action_result": result})


class RescheduleTool(BaseTool):
    name = "order_reschedule"
    description = "Reschedule an existing booking order."
    permission = "order:reschedule"
    required_permissions = {"order:reschedule", "external_api:local_life", "privacy:user_context"}

    def __init__(self, client: LocalLifeServiceClient | None = None) -> None:
        self.client = client or LocalLifeServiceClient()

    async def arun(self, payload: dict[str, Any]) -> ToolResult:
        try:
            result = await self.client.reschedule_order(payload)
        except Exception as exc:
            return ToolResult(ok=False, error=str(exc))
        return ToolResult(data={"action_result": result})


class CancelOrderTool(BaseTool):
    name = "order_cancel"
    description = "Cancel an existing booking order."
    permission = "order:cancel"
    required_permissions = {"order:cancel", "external_api:local_life", "order:read"}

    def __init__(self, client: LocalLifeServiceClient | None = None) -> None:
        self.client = client or LocalLifeServiceClient()

    async def arun(self, payload: dict[str, Any]) -> ToolResult:
        try:
            result = await self.client.cancel_order(payload)
        except Exception as exc:
            return ToolResult(ok=False, error=str(exc))
        return ToolResult(data={"action_result": result})


class ReviewOrderTool(BaseTool):
    name = "order_review"
    description = "Submit a review for a completed booking order."
    permission = "order:review"
    required_permissions = {"order:review", "external_api:local_life", "privacy:user_context"}

    def __init__(self, client: LocalLifeServiceClient | None = None) -> None:
        self.client = client or LocalLifeServiceClient()

    async def arun(self, payload: dict[str, Any]) -> ToolResult:
        try:
            result = await self.client.review_order(payload)
        except Exception as exc:
            return ToolResult(ok=False, error=str(exc))
        return ToolResult(data={"action_result": result})
