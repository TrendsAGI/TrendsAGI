from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
import hashlib
import json
import time
from typing import Any, Dict, Iterable, List, Optional

import requests

from .. import exceptions
from .. import models


@dataclass
class ExecutionResult:
    platform: str
    success: bool
    idempotency_key: str
    response: Dict[str, Any]
    dry_run: bool = False


class PlatformExecutionError(exceptions.TrendsAGIError):
    """Raised when a platform audience-injection call fails."""

    def __init__(self, platform: str, detail: str, status_code: Optional[int] = None):
        self.platform = platform
        self.detail = detail
        self.status_code = status_code
        if status_code is None:
            message = f"{platform} execution failed: {detail}"
        else:
            message = f"{platform} execution failed ({status_code}): {detail}"
        super().__init__(message)


class AdPlatformExecutor(ABC):
    platform_name: str = "base"
    required_credentials: Iterable[str] = ()

    def __init__(
        self,
        credentials: Dict[str, str],
        *,
        base_url: str,
        session: Optional[requests.Session] = None,
        timeout: float = 30.0,
    ):
        self.credentials = credentials or {}
        self.base_url = base_url.rstrip("/")
        self.session = session or requests.Session()
        self.timeout = timeout
        self._validate_credentials()

    def _validate_credentials(self) -> None:
        missing = [key for key in self.required_credentials if not self.credentials.get(key)]
        if missing:
            raise ValueError(
                f"Missing required credentials for {self.platform_name}: {', '.join(missing)}"
            )

    @staticmethod
    def _string_list(values: Iterable[str]) -> List[str]:
        out: List[str] = []
        seen = set()
        for value in values:
            value = (value or "").strip()
            if not value:
                continue
            if value in seen:
                continue
            seen.add(value)
            out.append(value)
        return out

    def _interest_keywords(self, insight: models.AIInsight) -> List[str]:
        if insight.audience_injection and insight.audience_injection.interest_keywords:
            return self._string_list(insight.audience_injection.interest_keywords)

        keywords: List[str] = []
        keywords.extend(
            self._string_list(
                (insight.ad_platform_targeting or {}).get("primary_audience_keywords", [])
            )
        )
        keywords.extend(
            self._string_list(
                (insight.ad_platform_targeting or {}).get("secondary_audience_keywords", [])
            )
        )
        if not keywords:
            keywords.extend(self._string_list(insight.key_themes))
        return self._string_list(keywords)

    def _negative_keywords(self, insight: models.AIInsight) -> List[str]:
        if insight.audience_injection:
            return self._string_list(insight.audience_injection.negative_keywords)
        return []

    def _demographics(self, insight: models.AIInsight) -> Dict[str, Any]:
        if insight.audience_injection:
            return dict(insight.audience_injection.demographics or {})
        return {}

    def build_idempotency_key(self, insight: models.AIInsight, salt: str = "") -> str:
        basis = {
            "trend_id": insight.trend_id,
            "platform": self.platform_name,
            "keywords": self._interest_keywords(insight),
            "negative_keywords": self._negative_keywords(insight),
            "salt": salt,
            "ts_hour": int(time.time() // 3600),
        }
        raw = json.dumps(basis, sort_keys=True, separators=(",", ":"))
        digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()
        return digest[:32]

    def _request(
        self,
        method: str,
        endpoint: str,
        *,
        headers: Optional[Dict[str, str]] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        url = f"{self.base_url}{endpoint}"
        try:
            response = self.session.request(
                method,
                url,
                headers=headers,
                timeout=self.timeout,
                **kwargs,
            )
        except requests.RequestException as exc:
            raise PlatformExecutionError(self.platform_name, f"network error: {exc}") from exc

        if 200 <= response.status_code < 300:
            if response.content:
                try:
                    parsed = response.json()
                    if isinstance(parsed, dict):
                        return parsed
                    return {"data": parsed}
                except ValueError:
                    return {"raw": response.text}
            return {}

        detail = response.text
        try:
            detail_json = response.json()
            if isinstance(detail_json, dict):
                detail = detail_json.get("error", detail_json.get("message", detail))
        except ValueError:
            pass

        raise PlatformExecutionError(
            self.platform_name,
            str(detail),
            status_code=response.status_code,
        )

    @abstractmethod
    def build_targeting_payload(self, insight: models.AIInsight, **kwargs: Any) -> Dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def apply_targeting(self, insight: models.AIInsight, **kwargs: Any) -> ExecutionResult:
        raise NotImplementedError

