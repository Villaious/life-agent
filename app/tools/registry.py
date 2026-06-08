from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from app.core.exceptions import ToolNotFoundError
from app.tools.base import BaseTool


ToolHandler = Callable[[dict[str, Any]], Awaitable[dict[str, Any]]]


@dataclass(frozen=True)
class ToolSpec:
    name: str
    permission: str
    handler: ToolHandler


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, BaseTool | ToolSpec] = {}

    def register(self, tool: BaseTool | ToolSpec) -> None:
        self._tools[tool.name] = tool

    def get(self, name: str) -> BaseTool | ToolSpec:
        if name not in self._tools:
            raise ToolNotFoundError(f"Tool not found: {name}")
        return self._tools[name]

    def list(self) -> list[BaseTool | ToolSpec]:
        return list(self._tools.values())
