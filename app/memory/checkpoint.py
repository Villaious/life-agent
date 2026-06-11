import json
from typing import Any

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from app.core.config import settings
from app.db.models import SessionCheckpointRecord
from app.db.session import SessionLocal
from app.models.booking import BookingRequest
from app.models.state import BookingGraphState

_MEMORY_CHECKPOINTS: dict[str, dict[str, Any]] = {}


class SessionCheckpointStore:
    def __init__(self, backend: str | None = None) -> None:
        self.backend = backend or settings.session_checkpoint_backend

    async def load(self, request: BookingRequest) -> dict[str, Any]:
        if not request.session_id:
            return {}

        if self.backend == "postgres":
            return await self._load_postgres(request)
        if self.backend == "redis":
            return await self._load_redis(request)
        return _MEMORY_CHECKPOINTS.get(self._key(request), {})

    async def save(self, state: BookingGraphState) -> None:
        request = state["request"]
        if not request.session_id:
            return

        payload = {
            "intent": state.get("intent"),
            "missing_fields": state.get("missing_fields", []),
            "current_step": state.get("current_step"),
            "response": state.get("response").model_dump(mode="json")
            if state.get("response")
            else None,
        }

        if self.backend == "postgres":
            await self._save_postgres(request, payload)
            return
        if self.backend == "redis":
            await self._save_redis(request, payload)
            return

        _MEMORY_CHECKPOINTS[self._key(request)] = payload

    def merge_request_context(
        self,
        request: BookingRequest,
        checkpoint: dict[str, Any],
    ) -> BookingRequest:
        intent = checkpoint.get("intent") or {}
        context = dict(request.context)
        context.setdefault("location", intent.get("location"))
        context.setdefault("time_preference", intent.get("time_preference"))
        context = {key: value for key, value in context.items() if value is not None}
        return request.model_copy(update={"context": context})

    def _key(self, request: BookingRequest) -> str:
        return f"{request.user_id}:{request.session_id}"

    async def _load_redis(self, request: BookingRequest) -> dict[str, Any]:
        from redis.asyncio import Redis

        redis = Redis.from_url(settings.redis_url, decode_responses=True)
        raw = await redis.get(self._key(request))
        await redis.aclose()
        return json.loads(raw) if raw else {}

    async def _save_redis(self, request: BookingRequest, payload: dict[str, Any]) -> None:
        from redis.asyncio import Redis

        redis = Redis.from_url(settings.redis_url, decode_responses=True)
        await redis.set(
            self._key(request),
            json.dumps(payload, ensure_ascii=False),
            ex=settings.session_checkpoint_ttl_seconds,
        )
        await redis.aclose()

    async def _load_postgres(self, request: BookingRequest) -> dict[str, Any]:
        try:
            async with SessionLocal() as session:
                result = await session.execute(
                    select(SessionCheckpointRecord).where(
                        SessionCheckpointRecord.user_id == request.user_id,
                        SessionCheckpointRecord.session_id == request.session_id,
                    )
                )
                record = result.scalar_one_or_none()
                return record.payload if record else {}
        except Exception:
            return {}

    async def _save_postgres(self, request: BookingRequest, payload: dict[str, Any]) -> None:
        try:
            async with SessionLocal.begin() as session:
                statement = insert(SessionCheckpointRecord).values(
                    user_id=request.user_id,
                    session_id=request.session_id,
                    payload=payload,
                )
                statement = statement.on_conflict_do_update(
                    index_elements=["user_id", "session_id"],
                    set_={"payload": payload},
                )
                await session.execute(statement)
        except Exception:
            return
