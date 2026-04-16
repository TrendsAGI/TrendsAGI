class TrendsAGIError(Exception):
    """Base exception for the TrendsAGI Python package."""


class ConfigurationError(TrendsAGIError):
    """Raised when required configuration is missing or invalid."""
