import os
from typing import Any

import httpx
from pydantic import BaseModel, Field

from app.core.config import settings
from app.core.exceptions import LLMProviderError
from app.core.message import Message


PROVIDER_DEFAULTS = {
    "openai": {
        "base_url": "https://api.openai.com/v1",
        "api_key_env": "OPENAI_API_KEY",
        "model": "gpt-4.1",
    },
    "modelscope": {
        "base_url": "https://api-inference.modelscope.cn/v1",
        "api_key_env": "MODELSCOPE_API_KEY",
        "model": "Qwen/Qwen2.5-72B-Instruct",
    },
    "zhipu": {
        "base_url": "https://open.bigmodel.cn/api/paas/v4",
        "api_key_env": "ZHIPUAI_API_KEY",
        "model": "glm-4-plus",
    },
    "ollama": {
        "base_url": "http://localhost:11434/v1",
        "api_key_env": "OLLAMA_API_KEY",
        "model": "qwen2.5:7b",
    },
    "openai-compatible": {
        "base_url": "https://api.openai.com/v1",
        "api_key_env": "LLM_API_KEY",
        "model": "gpt-4.1",
    },
}


class LLMConfig(BaseModel):
    provider: str = settings.llm_provider
    model: str = settings.llm_model
    api_key: str = settings.llm_api_key
    base_url: str = settings.llm_base_url
    temperature: float = settings.llm_temperature
    timeout: float = settings.llm_timeout
    dry_run: bool = settings.llm_dry_run
    extra_headers: dict[str, str] = Field(default_factory=dict)


class HelloAgentsLLM:
    def __init__(self, config: LLMConfig | None = None, **overrides: Any) -> None:
        values = (config.model_dump() if config else LLMConfig().model_dump()) | overrides
        self.config = self._resolve_config(LLMConfig(**values))

    @property
    def is_live(self) -> bool:
        if self.config.dry_run:
            return False
        return bool(self.config.api_key) or self.config.provider == "ollama"

    async def think(self, messages: list[Message]) -> str:
        if not self.is_live:
            last_user = next((m.content for m in reversed(messages) if m.role == "user"), "")
            return f"开发模式回复：我已经收到你的请求：{last_user}"

        payload = {
            "model": self.config.model,
            "messages": [message.to_dict() for message in messages],
            "temperature": self.config.temperature,
        }
        headers = dict(self.config.extra_headers)
        if self.config.api_key:
            headers["Authorization"] = f"Bearer {self.config.api_key}"

        async with httpx.AsyncClient(timeout=self.config.timeout) as client:
            response = await client.post(
                f"{self.config.base_url.rstrip('/')}/chat/completions",
                json=payload,
                headers=headers,
            )
            response.raise_for_status()
            data = response.json()

        try:
            return data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise LLMProviderError("LLM provider returned an unexpected response shape.") from exc

    async def complete(self, prompt: str, system_prompt: str | None = None) -> str:
        messages = []
        if system_prompt:
            messages.append(Message(role="system", content=system_prompt))
        messages.append(Message(role="user", content=prompt))
        return await self.think(messages)

    def _resolve_config(self, config: LLMConfig) -> LLMConfig:
        provider = config.provider.lower()
        defaults = PROVIDER_DEFAULTS.get(provider, PROVIDER_DEFAULTS["openai-compatible"])
        api_key = (
            config.api_key
            or os.getenv(defaults["api_key_env"])
            or os.getenv("OPENAI_API_KEY")
            or ""
        )
        base_url = config.base_url or defaults["base_url"]
        model = config.model or defaults["model"]
        return config.model_copy(
            update={
                "provider": provider,
                "api_key": api_key,
                "base_url": base_url,
                "model": model,
            }
        )
