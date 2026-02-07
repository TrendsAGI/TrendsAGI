from .client import TrendsAGIClient
from . import exceptions

from .integrations import (
    AdPlatformExecutor,
    ExecutionResult,
    PlatformExecutionError,
    GoogleAdsExecutor,
    MetaAdsExecutor,
    TikTokAdsExecutor,
    LinkedInAdsExecutor,
)

__all__ = [
    "TrendsAGIClient",
    "exceptions",
    "AdPlatformExecutor",
    "ExecutionResult",
    "PlatformExecutionError",
    "GoogleAdsExecutor",
    "MetaAdsExecutor",
    "TikTokAdsExecutor",
    "LinkedInAdsExecutor",
]

