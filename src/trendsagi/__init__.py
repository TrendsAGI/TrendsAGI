from importlib.metadata import PackageNotFoundError, version

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
from .models import AIInsight, AudienceInjection

try:
    __version__ = version("trendsagi")
except PackageNotFoundError:
    __version__ = "0.0.0"

__all__ = [
    "__version__",
    "exceptions",
    "AIInsight",
    "AudienceInjection",
    "AdPlatformExecutor",
    "ExecutionResult",
    "PlatformExecutionError",
    "GoogleAdsExecutor",
    "MetaAdsExecutor",
    "TikTokAdsExecutor",
    "LinkedInAdsExecutor",
]
