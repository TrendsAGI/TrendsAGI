from __future__ import annotations

from typing import Any, Dict, List

from .base import AdPlatformExecutor, ExecutionResult
from .. import models


class GoogleAdsExecutor(AdPlatformExecutor):
    platform_name = "google_ads"
    required_credentials = ("access_token", "developer_token")

    def __init__(self, credentials: Dict[str, str], **kwargs: Any):
        self.api_version = kwargs.pop("api_version", "v23")
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

    def build_targeting_payload(
        self,
        insight: models.AIInsight,
        *,
        customer_id: str,
        campaign_id: str,
    ) -> Dict[str, Any]:
        keywords = self._interest_keywords(insight)
        negative_keywords = self._negative_keywords(insight)
        operations: List[Dict[str, Any]] = []

        campaign_resource = f"customers/{customer_id}/campaigns/{campaign_id}"
        for text in keywords:
            operations.append(
                {
                    "create": {
                        "campaign": campaign_resource,
                        "keyword": {"text": text, "matchType": "BROAD"},
                        "negative": False,
                    }
                }
            )
        for text in negative_keywords:
            operations.append(
                {
                    "create": {
                        "campaign": campaign_resource,
                        "keyword": {"text": text, "matchType": "BROAD"},
                        "negative": True,
                    }
                }
            )

        return {"operations": operations}

    def apply_targeting(
        self,
        insight: models.AIInsight,
        *,
        customer_id: str,
        campaign_id: str,
        idempotency_key: str = "",
        dry_run: bool = False,
        partial_failure: bool = True,
        validate_only: bool = False,
        strict_mode: bool = False,
    ) -> ExecutionResult:
        customer_id = self._normalize_customer_id(customer_id)
        campaign_id = self._normalize_customer_id(campaign_id)
        if strict_mode:
            self._require_numeric_id(customer_id, "customer_id")
            self._require_numeric_id(campaign_id, "campaign_id")

        idempotency_key = idempotency_key or self.build_idempotency_key(
            insight, salt=f"{customer_id}:{campaign_id}"
        )
        request_body = self.build_targeting_payload(
            insight,
            customer_id=customer_id,
            campaign_id=campaign_id,
        )
        request_body["partialFailure"] = partial_failure
        request_body["validateOnly"] = validate_only

        if strict_mode and not request_body.get("operations"):
            raise ValueError(
                "Google strict_mode requires at least one keyword operation for campaign criteria mutation."
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
            "Authorization": f"Bearer {self.credentials['access_token']}",
            "developer-token": self.credentials["developer_token"],
            "Content-Type": "application/json",
            "x-goog-request-params": f"customer_id={customer_id}",
        }
        if self.credentials.get("login_customer_id"):
            login_customer_id = self._normalize_customer_id(
                self.credentials["login_customer_id"]
            )
            if strict_mode:
                self._require_numeric_id(login_customer_id, "login_customer_id")
            headers["login-customer-id"] = login_customer_id

        response = self._request(
            "POST",
            f"/{self.api_version}/customers/{customer_id}/campaignCriteria:mutate",
            headers=headers,
            json=request_body,
        )
        return ExecutionResult(
            platform=self.platform_name,
            success=True,
            idempotency_key=idempotency_key,
            response=response,
        )
