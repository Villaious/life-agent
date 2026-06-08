from typing import Any

from app.tools.policy import ToolContext, ToolPolicy
from app.tools.registry import ToolRegistry


class ToolSandbox:
    def __init__(self, registry: ToolRegistry, policy: ToolPolicy) -> None:
        self.registry = registry
        self.policy = policy

    async def call(self, name: str, payload: dict[str, Any], context: ToolContext) -> dict[str, Any]:
        spec = self.registry.get(name)
        permissions = spec.permissions if hasattr(spec, "permissions") else spec.permission
        if not self.policy.can_call(permissions, context):
            return {"ok": False, "error": "permission_denied", "tool": name}
        if hasattr(spec, "arun"):
            result = await spec.arun(payload)
            return result.model_dump()
        return await spec.handler(payload)
