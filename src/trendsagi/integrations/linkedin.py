from __future__ import annotations

from typing import Any, Dict, List
from urllib.parse import quote

from .base import AdPlatformExecutor, ExecutionResult
from .. import models


class LinkedInAdsExecutor(AdPlatformExecutor):
    platform_name = "linkedin_ads"
    required_credentials = ("access_token",)

    def __init__(self, credentials: Dict[str, str], **kwargs: Any):
        self.api_version = kwargs.pop("api_version", "202601")
        super().__init__(
            credentials,
            base_url=kwargs.pop("base_url", "https://api.linkedin.com"),
            **kwargs,
        )

    @staticmethod
    def _default_interface_locales(country: str, language: str) -> List[Dict[str, str]]:
        return [{"country": country.upper(), "language": language.lower()}]

    def _platform_payload(self, insight: models.AIInsight) -> Dict[str, Any]:
        if not insight.audience_injection:
            return {}
        payloads = insight.audience_injection.platform_payloads or {}
        if not isinstance(payloads, dict):
            return {}
        for key in ("linkedin", "linkedin_ads", "linkedIn"):
            payload = payloads.get(key)
            if isinstance(payload, dict):
                return payload
        return {}

    def build_targeting_payload(
        self,
        insight: models.AIInsight,
        *,
        locale_country: str = "US",
        locale_language: str = "en",
    ) -> Dict[str, Any]:
        platform_payload = self._platform_payload(insight)
        if "targetingCriteria" in platform_payload and isinstance(platform_payload["targetingCriteria"], dict):
            return {"targetingCriteria": platform_payload["targetingCriteria"]}
        if "include" in platform_payload and isinstance(platform_payload.get("include"), dict):
            targeting: Dict[str, Any] = {"include": platform_payload["include"]}
            if isinstance(platform_payload.get("exclude"), dict):
                targeting["exclude"] = platform_payload["exclude"]
            return {"targetingCriteria": targeting}

        keywords = self._interest_keywords(insight)
        negatives = self._negative_keywords(insight)
        demographics = self._demographics(insight)
        locales = self._default_interface_locales(locale_country, locale_language)

        include_or: List[Dict[str, Any]] = []
        for keyword in keywords:
            include_or.append(
                {
                    "facet": "SKILLS",
                    "targetingValues": [{"name": keyword}],
                    "interfaceLocales": locales,
                }
            )
        for region in demographics.get("regions", []) if isinstance(demographics, dict) else []:
            include_or.append(
                {
                    "facet": "GEO",
                    "targetingValues": [{"name": region}],
                    "interfaceLocales": locales,
                }
            )

        targeting_criteria: Dict[str, Any] = {}
        if include_or:
            targeting_criteria["include"] = {"and": [{"or": include_or}]}

        if negatives:
            exclude_or = [
                {
                    "facet": "SKILLS",
                    "targetingValues": [{"name": keyword}],
                    "interfaceLocales": locales,
                }
                for keyword in negatives
            ]
            targeting_criteria["exclude"] = {"and": [{"or": exclude_or}]}

        return {"targetingCriteria": targeting_criteria}

    def apply_targeting(
        self,
        insight: models.AIInsight,
        *,
        campaign_urn: str,
        idempotency_key: str = "",
        dry_run: bool = False,
        locale_country: str = "US",
        locale_language: str = "en",
        strict_mode: bool = False,
    ) -> ExecutionResult:
        campaign_urn = str(campaign_urn or "").strip()
        if not campaign_urn:
            raise ValueError("campaign_urn must be provided.")
        if strict_mode and not campaign_urn.startswith("urn:li:sponsoredCampaign:"):
            raise ValueError(
                "LinkedIn strict_mode requires campaign_urn in format 'urn:li:sponsoredCampaign:<id>'."
            )

        if strict_mode:
            platform_payload = self._platform_payload(insight)
            has_explicit_targeting = isinstance(
                platform_payload.get("targetingCriteria"), dict
            ) or isinstance(platform_payload.get("include"), dict)
            if not has_explicit_targeting:
                raise ValueError(
                    "LinkedIn strict_mode requires explicit targeting criteria in "
                    "insight.audience_injection.platform_payloads['linkedin']."
                )

        idempotency_key = idempotency_key or self.build_idempotency_key(insight, salt=campaign_urn)
        payload = self.build_targeting_payload(
            insight,
            locale_country=locale_country,
            locale_language=locale_language,
        )
        if strict_mode:
            targeting_criteria = payload.get("targetingCriteria")
            if not isinstance(targeting_criteria, dict) or not targeting_criteria:
                raise ValueError(
                    "LinkedIn strict_mode requires non-empty targetingCriteria."
                )
            if "include" not in targeting_criteria:
                raise ValueError(
                    "LinkedIn strict_mode requires targetingCriteria.include."
                )

        patch_body = {
            "patch": {
                "$set": {
                    "targetingCriteria": payload.get("targetingCriteria", {}),
                }
            }
        }

        if dry_run:
            return ExecutionResult(
                platform=self.platform_name,
                success=True,
                idempotency_key=idempotency_key,
                response=patch_body,
                dry_run=True,
            )

        headers = {
            "Authorization": f"Bearer {self.credentials['access_token']}",
            "LinkedIn-Version": self.api_version,
            "X-Restli-Protocol-Version": "2.0.0",
            "X-RestLi-Method": "PARTIAL_UPDATE",
            "Content-Type": "application/json",
        }
        encoded_campaign_urn = quote(campaign_urn, safe="")
        response = self._request(
            "POST",
            f"/rest/adCampaigns/{encoded_campaign_urn}",
            headers=headers,
            json=patch_body,
        )
        return ExecutionResult(
            platform=self.platform_name,
            success=True,
            idempotency_key=idempotency_key,
            response=response,
        )
