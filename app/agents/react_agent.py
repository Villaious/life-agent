from typing import Any

from app.core.agent import BaseAgent
from app.tools.policy import ToolContext


class ReActAgent(BaseAgent):
    async def run(self, user_input: str, **kwargs: object) -> str:
        context = kwargs.get("tool_context")
        if not isinstance(context, ToolContext):
            context = ToolContext(user_id="anonymous", task_id=None, permissions=set())

        tool_list = [tool.schema() for tool in self.tools.list()]
        prompt = f"{user_input}\n\n可用工具：{tool_list}\n请先思考，再给出下一步。"
        response = await self.call_llm(prompt)
        self.history.add("user", user_input)
        self.history.add("assistant", response)
        return response

    async def call_tool(self, name: str, payload: dict[str, Any]) -> dict[str, Any]:
        tool = self.tools.get(name)
        result = await tool.arun(payload)
        return result.model_dump()
