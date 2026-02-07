from __future__ import annotations

import hashlib
import hmac
import json
from typing import Any, Dict, Optional

from .base import AdPlatformExecutor, ExecutionResult, PlatformExecutionError
from .. import models


class MetaAdsExecutor(AdPlatformExecutor):
    platform_name = "meta_ads"
    required_credentials = ("access_token",)

    def __init__(self, credentials: Dict[str, str], **kwargs: Any):
        self.api_version = kwargs.pop("api_version", "v24.0")
        super().__init__(
            credentials,
            base_url=kwargs.pop("base_url", "https://graph.facebook.com"),
            **kwargs,
        )

    def _appsecret_proof(self) -> str:
        app_secret = self.credentials.get("app_secret")
        if not app_secret:
            return ""
        return hmac.new(
            app_secret.encode("utf-8"),
            self.credentials["access_token"].encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

    def _search_ad_interest(self, keyword: str) -> Dict[str, str]:
        if not keyword:
            return {}
        headers = {"Authorization": f"Bearer {self.credentials['access_token']}"}
        params: Dict[str, Any] = {
            "type": "adinterest",
            "q": keyword,
            "limit": 1,
        }
        proof = self._appsecret_proof()
        if proof:
            params["appsecret_proof"] = proof

        response = self._request(
            "GET",
            f"/{self.api_version}/search",
            headers=headers,
            params=params,
        )
        candidates = response.get("data", [])
        if not isinstance(candidates, list) or not candidates:
            return {}
        first = candidates[0]
        if not isinstance(first, dict):
            return {}

        interest_id = first.get("id")
        interest_name = first.get("name") or keyword
        if not interest_id:
            return {}
        return {"id": str(interest_id), "name": str(interest_name)}

    def build_targeting_payload(
        self,
        insight: models.AIInsight,
        *,
        resolved_interests: Optional[Dict[str, Dict[str, str]]] = None,
        resolved_excluded_interests: Optional[Dict[str, Dict[str, str]]] = None,
    ) -> Dict[str, Any]:
        keywords = self._interest_keywords(insight)
        negatives = self._negative_keywords(insight)
        demographics = self._demographics(insight)

        resolved_interests = resolved_interests or {}
        resolved_excluded_interests = resolved_excluded_interests or {}

        interests = [
            resolved_interests.get(keyword, {"name": keyword})
            for keyword in keywords
        ]
        targeting: Dict[str, Any] = {"interests": interests}
        if negatives:
            targeting["excluded_interests"] = [
                resolved_excluded_interests.get(keyword, {"name": keyword})
                for keyword in negatives
            ]

        regions = demographics.get("regions") if isinstance(demographics, dict) else None
        if isinstance(regions, list) and regions:
            countries = [
                r.upper()
                for r in regions
                if isinstance(r, str) and len(r.strip()) == 2 and r.strip().isalpha()
            ]
            if countries:
                targeting["geo_locations"] = {"countries": sorted(set(countries))}

        ages = demographics.get("ages") if isinstance(demographics, dict) else None
        if isinstance(ages, list) and ages:
            # Meta expects numeric ages. We map common ranges conservatively.
            age_floor = []
            age_ceiling = []
            for age_range in ages:
                if isinstance(age_range, str) and "-" in age_range:
                    lo, hi = age_range.split("-", 1)
                    if lo.isdigit():
                        age_floor.append(int(lo))
                    if hi.isdigit():
                        age_ceiling.append(int(hi))
            if age_floor:
                targeting["age_min"] = min(age_floor)
            if age_ceiling:
                targeting["age_max"] = max(age_ceiling)

        genders = demographics.get("genders") if isinstance(demographics, dict) else None
        if isinstance(genders, list) and genders:
            code_map = {"male": 1, "female": 2}
            resolved = [code_map[g.lower()] for g in genders if isinstance(g, str) and g.lower() in code_map]
            if resolved:
                targeting["genders"] = resolved

        return {"targeting": targeting}

    def apply_targeting(
        self,
        insight: models.AIInsight,
        *,
        adset_id: str,
        idempotency_key: str = "",
        dry_run: bool = False,
        resolve_interests: bool = True,
        strict_mode: bool = False,
    ) -> ExecutionResult:
        adset_id = str(adset_id or "").strip()
        if not adset_id:
            raise ValueError("adset_id must be provided.")
        if strict_mode and not adset_id.isdigit():
            raise ValueError("Meta strict_mode requires a numeric adset_id.")

        idempotency_key = idempotency_key or self.build_idempotency_key(insight, salt=adset_id)
        resolved_interests: Dict[str, Dict[str, str]] = {}
        resolved_excluded_interests: Dict[str, Dict[str, str]] = {}
        unresolved_interests = []
        unresolved_excluded_interests = []
        if resolve_interests and not dry_run:
            for keyword in self._interest_keywords(insight):
                try:
                    resolved = self._search_ad_interest(keyword)
                except PlatformExecutionError:
                    resolved = {}
                if resolved:
                    resolved_interests[keyword] = resolved
                else:
                    unresolved_interests.append(keyword)
            for keyword in self._negative_keywords(insight):
                try:
                    resolved = self._search_ad_interest(keyword)
                except PlatformExecutionError:
                    resolved = {}
                if resolved:
                    resolved_excluded_interests[keyword] = resolved
                else:
                    unresolved_excluded_interests.append(keyword)

        payload = self.build_targeting_payload(
            insight,
            resolved_interests=resolved_interests,
            resolved_excluded_interests=resolved_excluded_interests,
        )
        if strict_mode:
            if unresolved_interests:
                raise ValueError(
                    "Meta strict_mode could not resolve ad interests: "
                    + ", ".join(unresolved_interests)
                )
            if unresolved_excluded_interests:
                raise ValueError(
                    "Meta strict_mode could not resolve excluded ad interests: "
                    + ", ".join(unresolved_excluded_interests)
                )
            targeting = payload.get("targeting", {})
            interests = targeting.get("interests", [])
            if not interests:
                raise ValueError(
                    "Meta strict_mode requires at least one resolved interest in targeting."
                )
            missing_interest_ids = [
                item.get("name", "unknown")
                for item in interests
                if not isinstance(item, dict) or not item.get("id")
            ]
            if missing_interest_ids:
                raise ValueError(
                    "Meta strict_mode requires interest IDs. Missing IDs for: "
                    + ", ".join(missing_interest_ids)
                )
            excluded_interests = targeting.get("excluded_interests", [])
            missing_excluded_ids = [
                item.get("name", "unknown")
                for item in excluded_interests
                if isinstance(item, dict) and not item.get("id")
            ]
            if missing_excluded_ids:
                raise ValueError(
                    "Meta strict_mode requires excluded interest IDs. Missing IDs for: "
                    + ", ".join(missing_excluded_ids)
                )

        if dry_run:
            return ExecutionResult(
                platform=self.platform_name,
                success=True,
                idempotency_key=idempotency_key,
                response=payload,
                dry_run=True,
            )

        headers = {
            "X-FB-Request-ID": idempotency_key,
            "Authorization": f"Bearer {self.credentials['access_token']}",
        }
        data = {
            "access_token": self.credentials["access_token"],
            "targeting": json.dumps(payload["targeting"]),
        }
        proof = self._appsecret_proof()
        if proof:
            data["appsecret_proof"] = proof
        response = self._request(
            "POST",
            f"/{self.api_version}/{adset_id}",
            headers=headers,
            data=data,
        )
        return ExecutionResult(
            platform=self.platform_name,
            success=True,
            idempotency_key=idempotency_key,
            response=response,
        )
