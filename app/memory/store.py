from typing import Any


class MemoryStore:
    async def get_user_profile(self, user_id: str) -> dict[str, Any]:
        return {"user_id": user_id, "preferences": {}}

    async def save_task_snapshot(self, user_id: str, task_id: str, payload: dict[str, Any]) -> None:
        return None
