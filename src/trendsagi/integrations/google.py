from __future__ import annotations

from typing import Any, Dict, List

from .base import AdPlatformExecutor, ExecutionResult
from .. import models


class GoogleAdsExecutor(AdPlatformExecutor):
    platform_name = "google_ads"
    required_credentials = ("access_token", "developer_token")

    def __init__(self, credentials: Dict[str, str], **kwargs: Any):
        self.api_version = kwargs.pop("api_version", "v26")
        super().__init__(
            credentials,
            base_url=kwargs.pop("base_url", "https://googleads.googleapis.com"),
            **kwargs,
        )

    @staticmethod
    def _normalize_customer_id(customer_id: str) -> str:
        return "".join(ch for ch in str(customer_id) if ch.isdigit())

    @staticmethod
    def _require_numeric_id(identifier: str, field_name: str) -> None:
        if not identifier:
            raise ValueError(f"{field_name} must be provided as a numeric identifier.")

    def _campaign_operations(
        self,
        insight: models.AIInsight,
        *,
        customer_id: str,
        campaign_id: str,
    ) -> List[Dict[str, Any]]:
        campaign_resource = f"customers/{customer_id}/campaigns/{campaign_id}"
        return [
            {
                "create": {
                    "campaign": campaign_resource,
                    "keyword": {"text": text, "matchType": "BROAD"},
                    "negative": True,
                }
            }
            for text in self._negative_keywords(insight)
        ]

    def _ad_group_operations(
        self,
        insight: models.AIInsight,
        *,
        customer_id: str,
        ad_group_id: str,
    ) -> List[Dict[str, Any]]:
        ad_group_resource = f"customers/{customer_id}/adGroups/{ad_group_id}"
        return [
            {
                "create": {
                    "adGroup": ad_group_resource,
                    "status": "ENABLED",
                    "keyword": {"text": text, "matchType": "BROAD"},
                }
            }
            for text in self._interest_keywords(insight)
        ]

    def build_campaign_targeting_payload(
        self,
        insight: models.AIInsight,
        *,
        customer_id: str,
        campaign_id: str,
    ) -> Dict[str, Any]:
        """Build the campaign criteria body, which may only exclude keywords."""
        return {
            "operations": self._campaign_operations(
                insight,
                customer_id=customer_id,
                campaign_id=campaign_id,
            )
        }

    def build_ad_group_targeting_payload(
        self,
        insight: models.AIInsight,
        *,
        customer_id: str,
        ad_group_id: str,
    ) -> Dict[str, Any]:
        """Build the ad group criteria body for positive keyword targeting."""
        return {
            "operations": self._ad_group_operations(
                insight,
                customer_id=customer_id,
                ad_group_id=ad_group_id,
            )
        }

    def build_targeting_payload(
        self,
        insight: models.AIInsight,
        *,
        customer_id: str,
        campaign_id: str,
        ad_group_id: str = "",
    ) -> Dict[str, Any]:
        campaign_operations = self._campaign_operations(
            insight,
            customer_id=customer_id,
            campaign_id=campaign_id,
        )
        ad_group_operations = (
            self._ad_group_operations(
                insight,
                customer_id=customer_id,
                ad_group_id=ad_group_id,
            )
            if ad_group_id
            else []
        )
        return {
            "campaign_operations": campaign_operations,
            "ad_group_operations": ad_group_operations,
            "operations": campaign_operations + ad_group_operations,
        }

    def apply_targeting(
        self,
        insight: models.AIInsight,
        *,
        customer_id: str,
        campaign_id: str,
        ad_group_id: str = "",
        idempotency_key: str = "",
        dry_run: bool = False,
        partial_failure: bool = True,
        validate_only: bool = False,
        strict_mode: bool = False,
    ) -> ExecutionResult:
        customer_id = self._normalize_customer_id(customer_id)
        campaign_id = self._normalize_customer_id(campaign_id)
        ad_group_id = self._normalize_customer_id(ad_group_id)
        if strict_mode:
            self._require_numeric_id(customer_id, "customer_id")
            self._require_numeric_id(campaign_id, "campaign_id")

        positive_keywords = self._interest_keywords(insight)
        if positive_keywords and not ad_group_id:
            raise ValueError(
                "Google Ads positive keywords require ad_group_id; campaign-level "
                "criteria support negative keywords only."
            )
        if strict_mode and positive_keywords:
            self._require_numeric_id(ad_group_id, "ad_group_id")

        idempotency_key = idempotency_key or self.build_idempotency_key(
            insight, salt=f"{customer_id}:{campaign_id}:{ad_group_id}"
        )
        campaign_payload = self.build_campaign_targeting_payload(
            insight,
            customer_id=customer_id,
            campaign_id=campaign_id,
        )
        ad_group_payload = (
            self.build_ad_group_targeting_payload(
                insight,
                customer_id=customer_id,
                ad_group_id=ad_group_id,
            )
            if ad_group_id
            else {"operations": []}
        )
        campaign_payload["partialFailure"] = partial_failure
        campaign_payload["validateOnly"] = validate_only
        ad_group_payload["partialFailure"] = partial_failure
        ad_group_payload["validateOnly"] = validate_only

        if strict_mode and not campaign_payload["operations"] and not ad_group_payload["operations"]:
            raise ValueError(
                "Google strict_mode requires at least one keyword operation for campaign or ad group criteria mutation."
            )

        if dry_run:
            return ExecutionResult(
                platform=self.platform_name,
                success=True,
                idempotency_key=idempotency_key,
                response={
                    # Keep the pre-0.17.1 keys for callers that preview the
                    # request, while exposing the two request bodies separately:
                    # a single mutate endpoint cannot carry both.
                    "operations": campaign_payload["operations"] + ad_group_payload["operations"],
                    "partialFailure": partial_failure,
                    "validateOnly": validate_only,
                    "campaign": campaign_payload,
                    "ad_group": ad_group_payload,
                },
                dry_run=True,
            )

        headers = {
            "Authorization": f"Bearer {self.credentials['access_token']}",
            "developer-token": self.credentials["developer_token"],
            "Content-Type": "application/json",
        }
        if self.credentials.get("login_customer_id"):
            login_customer_id = self._normalize_customer_id(
                self.credentials["login_customer_id"]
            )
            if strict_mode:
                self._require_numeric_id(login_customer_id, "login_customer_id")
            headers["login-customer-id"] = login_customer_id

        responses: Dict[str, Any] = {}
        if ad_group_payload["operations"]:
            responses["ad_group_criteria"] = self._request(
                "POST",
                f"/{self.api_version}/customers/{customer_id}/adGroupCriteria:mutate",
                headers=headers,
                json=ad_group_payload,
            )
        if campaign_payload["operations"]:
            responses["campaign_criteria"] = self._request(
                "POST",
                f"/{self.api_version}/customers/{customer_id}/campaignCriteria:mutate",
                headers=headers,
                json=campaign_payload,
            )

        if len(responses) == 1:
            response: Dict[str, Any] = next(iter(responses.values()))
        elif responses:
            response = responses
        else:
            response = {"operations": []}
        return ExecutionResult(
            platform=self.platform_name,
            success=True,
            idempotency_key=idempotency_key,
            response=response,
        )
