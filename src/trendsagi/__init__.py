from .client import TrendsAGIClient
from . import exceptions
from importlib.metadata import PackageNotFoundError, version

from .integrations import (
    AdPlatformExecutor,
    ExecutionResult,
    PlatformExecutionError,
    GoogleAdsExecutor,
    MetaAdsExecutor,
    TikTokAdsExecutor,
    LinkedInAdsExecutor,
)

try:
    __version__ = version("trendsagi")
except PackageNotFoundError:
    __version__ = "0.0.0"

__all__ = [
    "TrendsAGIClient",
    "__version__",
    "exceptions",
    "AdPlatformExecutor",
    "ExecutionResult",
    "PlatformExecutionError",
    "GoogleAdsExecutor",
    "MetaAdsExecutor",
    "TikTokAdsExecutor",
    "LinkedInAdsExecutor",
]
