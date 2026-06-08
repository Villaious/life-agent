import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

# 自动加载项目根目录下的 .env 文件
_dotenv_path = Path(__file__).resolve().parent.parent.parent / ".env"
load_dotenv(dotenv_path=_dotenv_path)


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
    booking_persistence_enabled: bool = False
    session_checkpoint_backend: str = "memory"
    session_checkpoint_ttl_seconds: int = 86400

    local_life_api_base_url: str = ""
    local_life_api_key: str = ""
    local_life_sandbox_base_url: str = ""
    local_life_sandbox_api_key: str = ""
    local_life_timeout: float = 15
    local_life_dry_run: bool = True

    llm_provider: str = "openai"
    llm_model: str = ""
    llm_api_key: str = ""
    llm_base_url: str = ""
    llm_temperature: float = 0.2
    llm_timeout: float = 60
    llm_dry_run: bool = False

    amap_api_key: str = ""
    amap_search_radius: int = 3000
    amap_timeout: float = 10

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
    booking_persistence_enabled=_get_bool("BOOKING_PERSISTENCE_ENABLED", False),
    session_checkpoint_backend=os.getenv("SESSION_CHECKPOINT_BACKEND", "memory"),
    session_checkpoint_ttl_seconds=int(os.getenv("SESSION_CHECKPOINT_TTL_SECONDS", "86400")),
    local_life_api_base_url=os.getenv("LOCAL_LIFE_API_BASE_URL", ""),
    local_life_api_key=os.getenv("LOCAL_LIFE_API_KEY", ""),
    local_life_sandbox_base_url=os.getenv("LOCAL_LIFE_SANDBOX_BASE_URL", ""),
    local_life_sandbox_api_key=os.getenv("LOCAL_LIFE_SANDBOX_API_KEY", ""),
    local_life_timeout=_get_float("LOCAL_LIFE_TIMEOUT", 15),
    local_life_dry_run=_get_bool("LOCAL_LIFE_DRY_RUN", True),
    llm_provider=os.getenv("LLM_PROVIDER", "openai"),
    llm_model=os.getenv("LLM_MODEL", ""),
    llm_api_key=os.getenv("LLM_API_KEY", ""),
    llm_base_url=os.getenv("LLM_BASE_URL", ""),
    llm_temperature=_get_float("LLM_TEMPERATURE", 0.2),
    llm_timeout=_get_float("LLM_TIMEOUT", 60),
    llm_dry_run=_get_bool("LLM_DRY_RUN", False),
    amap_api_key=os.getenv("AMAP_API_KEY", ""),
    amap_search_radius=int(os.getenv("AMAP_SEARCH_RADIUS", "3000")),
    amap_timeout=_get_float("AMAP_TIMEOUT", 10),
    tool_sandbox_enabled=_get_bool("TOOL_SANDBOX_ENABLED", True),
    tool_audit_enabled=_get_bool("TOOL_AUDIT_ENABLED", True),
)
