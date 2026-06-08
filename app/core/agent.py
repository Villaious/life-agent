from abc import ABC, abstractmethod

from app.core.llm import HelloAgentsLLM
from app.core.message import ConversationHistory, Message
from app.tools.base import BaseTool
from app.tools.registry import ToolRegistry


class BaseAgent(ABC):
    def __init__(
        self,
        name: str,
        llm: HelloAgentsLLM | None = None,
        system_prompt: str = "",
        tools: list[BaseTool] | None = None,
    ) -> None:
        self.name = name
        self.llm = llm or HelloAgentsLLM()
        self.system_prompt = system_prompt
        self.history = ConversationHistory()
        self.tools = ToolRegistry()

        for tool in tools or []:
            self.add_tool(tool)

    def add_tool(self, tool: BaseTool) -> None:
        self.tools.register(tool)

    def get_history(self) -> list[Message]:
        return self.history.to_messages()

    def clear_history(self) -> None:
        self.history.clear()

    def build_messages(self, user_input: str) -> list[Message]:
        messages: list[Message] = []
        if self.system_prompt:
            messages.append(Message(role="system", content=self.system_prompt))
        messages.extend(self.history.to_messages())
        messages.append(Message(role="user", content=user_input))
        return messages

    async def call_llm(self, user_input: str) -> str:
        return await self.llm.think(self.build_messages(user_input))

    @abstractmethod
    async def run(self, user_input: str, **kwargs: object) -> object:
        raise NotImplementedError
