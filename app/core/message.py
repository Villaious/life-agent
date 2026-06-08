from dataclasses import dataclass
from typing import Literal

MessageRole = Literal["system", "user", "assistant", "tool"]


@dataclass
class Message:
    role: MessageRole
    content: str
    name: str | None = None

    def to_dict(self) -> dict[str, str]:
        payload = {"role": self.role, "content": self.content}
        if self.name:
            payload["name"] = self.name
        return payload


class ConversationHistory:
    def __init__(self) -> None:
        self._messages: list[Message] = []

    def add(self, role: MessageRole, content: str, name: str | None = None) -> None:
        self._messages.append(Message(role=role, content=content, name=name))

    def extend(self, messages: list[Message]) -> None:
        self._messages.extend(messages)

    def clear(self) -> None:
        self._messages.clear()

    def to_messages(self) -> list[Message]:
        return list(self._messages)

    def to_openai_messages(self) -> list[dict[str, str]]:
        return [message.to_dict() for message in self._messages]

    def __len__(self) -> int:
        return len(self._messages)
