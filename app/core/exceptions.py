class AgentError(Exception):
    """Base error for the local agent framework."""


class LLMConfigError(AgentError):
    """Raised when LLM configuration is incomplete or invalid."""


class LLMProviderError(AgentError):
    """Raised when the configured LLM provider returns an invalid response."""


class ToolNotFoundError(AgentError):
    """Raised when an agent requests an unknown tool."""


class ToolPermissionError(AgentError):
    """Raised when a tool call is denied by policy."""
