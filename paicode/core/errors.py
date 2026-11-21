class PaicodeError(Exception):
    """Base error for recoverable Paicode failures."""


class PathSecurityError(PaicodeError):
    """Raised when a path escapes the project root or targets a sensitive entry."""


class ProviderError(PaicodeError):
    """Raised when a provider request cannot be completed."""


class ToolError(PaicodeError):
    """Raised when a tool call is invalid or cannot be executed."""


class ConfigError(PaicodeError):
    """Raised when the provider configuration is missing or malformed."""
