from __future__ import annotations

from typing import Any, Dict, List, Optional

from .base import AdPlatformExecutor, ExecutionResult, PlatformExecutionError
from .. import models


class TikTokAdsExecutor(AdPlatformExecutor):
    platform_name = "tiktok_ads"
    required_credentials = ("access_token", "advertiser_id")

    def __init__(self, credentials: Dict[str, str], **kwargs: Any):
        super().__init__(
            credentials,
            base_url=kwargs.pop("base_url", "https://business-api.tiktok.com"),
            **kwargs,
        )
        self.api_version = kwargs.pop("api_version", "v1.3")

    def _platform_payload(self, insight: models.AIInsight) -> Dict[str, Any]:
        if not insight.audience_injection:
            return {}
        payloads = insight.audience_injection.platform_payloads or {}
        if not isinstance(payloads, dict):
            return {}
        for key in ("tiktok", "tiktok_ads"):
            payload = payloads.get(key)
            if isinstance(payload, dict):
                return payload
        return {}

    def _resolve_interest_keyword_ids(
        self,
        keywords: List[str],
    ) -> List[str]:
        headers = {"Access-Token": self.credentials["access_token"]}
        resolved: List[str] = []
        seen = set()

        for keyword in keywords:
            try:
                response = self._request(
                    "GET",
                    f"/open_api/{self.api_version}/tool/interest_keyword/recommend/",
                    headers=headers,
                    params={
                        "advertiser_id": self.credentials["advertiser_id"],
                        "keyword": keyword,
                    },
                )
            except PlatformExecutionError:
                continue

            stack: List[Any] = [response]
            while stack:
                current = stack.pop()
                if isinstance(current, dict):
                    for key in ("interest_keyword_id", "keyword_id", "id"):
                        value = current.get(key)
                        if value is not None:
                            value_s = str(value).strip()
                            if value_s and value_s not in seen:
                                seen.add(value_s)
                                resolved.append(value_s)
                    for value in current.values():
                        if isinstance(value, (dict, list)):
                            stack.append(value)
                elif isinstance(current, list):
                    for item in current:
                        if isinstance(item, (dict, list)):
                            stack.append(item)
        return resolved

    def build_targeting_payload(
        self,
        insight: models.AIInsight,
        *,
        adgroup_id: str,
        resolved_interest_keyword_ids: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        platform_payload = self._platform_payload(insight)
        request_body: Dict[str, Any] = {
            "advertiser_id": self.credentials["advertiser_id"],
            "adgroup_id": adgroup_id,
        }

        provided_ids = platform_payload.get("interest_keyword_ids")
        if isinstance(provided_ids, list):
            request_body["interest_keyword_ids"] = self._string_list([str(v) for v in provided_ids])

        if resolved_interest_keyword_ids:
            merged = request_body.get("interest_keyword_ids", [])
            merged.extend(resolved_interest_keyword_ids)
            request_body["interest_keyword_ids"] = self._string_list([str(v) for v in merged])

        if not request_body.get("interest_keyword_ids"):
            keywords = self._interest_keywords(insight)
            if keywords:
                request_body["search_keywords"] = [{"keyword": keyword} for keyword in keywords]

        # Pass through explicitly provided platform-level fields that match
        # TikTok adgroup update body keys.
        for key in (
            "location_ids",
            "age_groups",
            "gender",
            "audience_ids",
            "excluded_audience_ids",
            "languages",
            "spending_power",
            "household_income",
            "targeting_expansion",
        ):
            value = platform_payload.get(key)
            if value is not None:
                request_body[key] = value

        return request_body

    def apply_targeting(
        self,
        insight: models.AIInsight,
        *,
        adgroup_id: str,
        idempotency_key: str = "",
        dry_run: bool = False,
        resolve_interest_keywords: bool = True,
        strict_mode: bool = False,
    ) -> ExecutionResult:
        adgroup_id = str(adgroup_id or "").strip()
        if not adgroup_id:
            raise ValueError("adgroup_id must be provided.")
        if strict_mode and not adgroup_id.isdigit():
            raise ValueError("TikTok strict_mode requires a numeric adgroup_id.")

        idempotency_key = idempotency_key or self.build_idempotency_key(insight, salt=adgroup_id)
        resolved_interest_keyword_ids: List[str] = []
        if resolve_interest_keywords and not dry_run:
            resolved_interest_keyword_ids = self._resolve_interest_keyword_ids(
                self._interest_keywords(insight)
            )

        request_body = self.build_targeting_payload(
            insight,
            adgroup_id=adgroup_id,
            resolved_interest_keyword_ids=resolved_interest_keyword_ids,
        )
        if strict_mode:
            interest_keyword_ids = request_body.get("interest_keyword_ids", [])
            if not interest_keyword_ids:
                raise ValueError(
                    "TikTok strict_mode requires resolved or provided interest_keyword_ids."
                )
            if request_body.get("search_keywords"):
                raise ValueError(
                    "TikTok strict_mode does not allow fallback search_keywords payloads."
                )

        if dry_run:
            return ExecutionResult(
                platform=self.platform_name,
                success=True,
                idempotency_key=idempotency_key,
                response=request_body,
                dry_run=True,
            )

        headers = {
            "Access-Token": self.credentials["access_token"],
            "Content-Type": "application/json",
        }
        response = self._request(
            "POST",
            f"/open_api/{self.api_version}/adgroup/update/",
            headers=headers,
            json=request_body,
        )
        return ExecutionResult(
            platform=self.platform_name,
            success=True,
            idempotency_key=idempotency_key,
            response=response,
        )
