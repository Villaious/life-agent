from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel, Field


class ToolResult(BaseModel):
    ok: bool = True
    data: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None


class BaseTool(ABC):
    name: str
    description: str
    permission: str = "tool:read"
    required_permissions: set[str] | None = None

    @abstractmethod
    async def arun(self, payload: dict[str, Any]) -> ToolResult:
        raise NotImplementedError

    def schema(self) -> dict[str, str]:
        return {
            "name": self.name,
            "description": self.description,
            "permission": ",".join(sorted(self.permissions)),
        }

    @property
    def permissions(self) -> set[str]:
        return self.required_permissions or {self.permission}
