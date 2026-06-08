from dataclasses import dataclass


@dataclass(frozen=True)
class ToolContext:
    user_id: str
    task_id: str | None
    permissions: set[str]
    privacy_scopes: set[str] | None = None


class ToolPolicy:
    def can_call(self, permissions: str | set[str], context: ToolContext) -> bool:
        required = {permissions} if isinstance(permissions, str) else permissions
        return required.issubset(context.permissions)
