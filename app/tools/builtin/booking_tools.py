from typing import Any

from app.integrations.local_life_client import LocalLifeServiceClient
from app.tools.base import BaseTool, ToolResult


class ServiceMatchTool(BaseTool):
    name = "service_match"
    description = "Match local life service providers by intent and location."
    permission = "booking:match"
    required_permissions = {"booking:match", "external_api:local_life", "privacy:user_context"}

    def __init__(self, client: LocalLifeServiceClient | None = None) -> None:
        self.client = client or LocalLifeServiceClient()

    async def arun(self, payload: dict[str, Any]) -> ToolResult:
        try:
            candidates = await self.client.match_services(payload)
        except Exception as exc:
            return ToolResult(ok=False, error=str(exc))
        return ToolResult(data={"candidates": candidates})


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
