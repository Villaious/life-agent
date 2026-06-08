import os
from dataclasses import dataclass


def _get_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.lower() in {"1", "true", "yes", "on"}


def _get_float(name: str, default: float) -> float:
    value = os.getenv(name)
    if value is None:
        return default
    return float(value)


@dataclass(frozen=True)
class Settings:
    app_name: str = "local-life-agent"
    app_env: str = "local"
    debug: bool = True

    database_url: str = "postgresql+asyncpg://agent:agent@localhost:5432/local_life_agent"
    redis_url: str = "redis://localhost:6379/0"

    local_life_api_base_url: str = ""
    local_life_api_key: str = ""
    local_life_timeout: float = 15
    local_life_dry_run: bool = True

    llm_provider: str = "openai"
    llm_model: str = ""
    llm_api_key: str = ""
    llm_base_url: str = ""
    llm_temperature: float = 0.2
    llm_timeout: float = 60
    llm_dry_run: bool = False

    tool_sandbox_enabled: bool = True
    tool_audit_enabled: bool = True


settings = Settings(
    app_name=os.getenv("APP_NAME", "local-life-agent"),
    app_env=os.getenv("APP_ENV", "local"),
    debug=_get_bool("DEBUG", True),
    database_url=os.getenv(
        "DATABASE_URL",
        "postgresql+asyncpg://agent:agent@localhost:5432/local_life_agent",
    ),
    redis_url=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
    local_life_api_base_url=os.getenv("LOCAL_LIFE_API_BASE_URL", ""),
    local_life_api_key=os.getenv("LOCAL_LIFE_API_KEY", ""),
    local_life_timeout=_get_float("LOCAL_LIFE_TIMEOUT", 15),
    local_life_dry_run=_get_bool("LOCAL_LIFE_DRY_RUN", True),
    llm_provider=os.getenv("LLM_PROVIDER", "openai"),
    llm_model=os.getenv("LLM_MODEL", ""),
    llm_api_key=os.getenv("LLM_API_KEY", ""),
    llm_base_url=os.getenv("LLM_BASE_URL", ""),
    llm_temperature=_get_float("LLM_TEMPERATURE", 0.2),
    llm_timeout=_get_float("LLM_TIMEOUT", 60),
    llm_dry_run=_get_bool("LLM_DRY_RUN", False),
    tool_sandbox_enabled=_get_bool("TOOL_SANDBOX_ENABLED", True),
    tool_audit_enabled=_get_bool("TOOL_AUDIT_ENABLED", True),
)
