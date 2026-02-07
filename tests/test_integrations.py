import json
import unittest

from trendsagi import models
from trendsagi.integrations import (
    GoogleAdsExecutor,
    LinkedInAdsExecutor,
    MetaAdsExecutor,
    TikTokAdsExecutor,
)


class DummyResponse:
    def __init__(self, status_code=200, payload=None):
        self.status_code = status_code
        self._payload = payload if payload is not None else {"ok": True}
        self.headers = {}
        self.text = json.dumps(self._payload)
        self.content = self.text.encode("utf-8")

    def json(self):
        return self._payload


class FakeSession:
    def __init__(self):
        self.calls = []

    def request(self, method, url, **kwargs):
        self.calls.append((method, url, kwargs))
        return DummyResponse(200, {"method": method, "url": url})


def make_insight():
    return models.AIInsight.model_validate(
        {
            "trend_id": 123,
            "key_themes": ["fitness"],
            "ad_platform_targeting": {
                "primary_audience_keywords": ["running shoes"],
                "secondary_audience_keywords": ["athleisure"],
            },
            "audience_injection": {
                "interest_keywords": ["running shoes"],
                "negative_keywords": ["cheap"],
                "demographics": {"ages": ["18-24"], "regions": ["US"]},
            },
        }
    )


def make_empty_insight():
    return models.AIInsight.model_validate(
        {
            "trend_id": 999,
            "key_themes": [],
            "ad_platform_targeting": {},
            "audience_injection": {
                "interest_keywords": [],
                "negative_keywords": [],
                "demographics": {},
            },
        }
    )


class IntegrationTests(unittest.TestCase):
    def test_google_executor_dry_run_and_apply(self):
        session = FakeSession()
        executor = GoogleAdsExecutor(
            {"access_token": "tok", "developer_token": "dev"},
            session=session,
        )
        insight = make_insight()
        dry_result = executor.apply_targeting(
            insight,
            customer_id="123456",
            campaign_id="987654",
            dry_run=True,
        )
        self.assertTrue(dry_result.dry_run)
        self.assertIn("operations", dry_result.response)
        self.assertIn("partialFailure", dry_result.response)
        self.assertIn("validateOnly", dry_result.response)

        live_result = executor.apply_targeting(
            insight,
            customer_id="123456",
            campaign_id="987654",
        )
        self.assertTrue(live_result.success)
        self.assertEqual(len(session.calls), 1)
        method, url, kwargs = session.calls[0]
        self.assertEqual(method, "POST")
        self.assertTrue(url.endswith("/v23/customers/123456/campaignCriteria:mutate"))
        self.assertIn("developer-token", kwargs["headers"])
        self.assertNotIn("x-idempotency-key", kwargs["headers"])

    def test_meta_executor_builds_targeting(self):
        session = FakeSession()
        executor = MetaAdsExecutor({"access_token": "tok"}, session=session)
        insight = make_insight()
        payload = executor.build_targeting_payload(insight)
        self.assertIn("targeting", payload)
        self.assertIn("interests", payload["targeting"])

        result = executor.apply_targeting(insight, adset_id="111")
        self.assertTrue(result.success)
        self.assertGreaterEqual(len(session.calls), 1)
        method, url, kwargs = session.calls[-1]
        self.assertEqual(method, "POST")
        self.assertTrue(url.endswith("/v24.0/111"))
        self.assertIn("Authorization", kwargs["headers"])

    def test_tiktok_executor_apply(self):
        session = FakeSession()
        executor = TikTokAdsExecutor(
            {"access_token": "tok", "advertiser_id": "adv-1"},
            session=session,
        )
        insight = make_insight()
        result = executor.apply_targeting(insight, adgroup_id="group-1")
        self.assertTrue(result.success)
        self.assertGreaterEqual(len(session.calls), 1)
        method, url, kwargs = session.calls[-1]
        self.assertEqual(method, "POST")
        self.assertTrue(url.endswith("/open_api/v1.3/adgroup/update/"))
        self.assertIn("Access-Token", kwargs["headers"])
        self.assertNotIn("X-Request-Id", kwargs["headers"])

    def test_linkedin_executor_apply(self):
        session = FakeSession()
        executor = LinkedInAdsExecutor({"access_token": "tok"}, session=session)
        insight = make_insight()
        result = executor.apply_targeting(insight, campaign_urn="urn:li:sponsoredCampaign:123")
        self.assertTrue(result.success)
        self.assertEqual(len(session.calls), 1)
        method, url, kwargs = session.calls[0]
        self.assertEqual(method, "POST")
        self.assertIn("/rest/adCampaigns/urn%3Ali%3AsponsoredCampaign%3A123", url)
        self.assertEqual(kwargs["headers"]["X-RestLi-Method"], "PARTIAL_UPDATE")

    def test_google_executor_strict_mode_requires_operations(self):
        session = FakeSession()
        executor = GoogleAdsExecutor(
            {"access_token": "tok", "developer_token": "dev"},
            session=session,
        )
        with self.assertRaises(ValueError):
            executor.apply_targeting(
                make_empty_insight(),
                customer_id="123456",
                campaign_id="987654",
                strict_mode=True,
            )

    def test_meta_executor_strict_mode_requires_resolved_interest_ids(self):
        session = FakeSession()
        executor = MetaAdsExecutor({"access_token": "tok"}, session=session)
        with self.assertRaises(ValueError):
            executor.apply_targeting(
                make_insight(),
                adset_id="111",
                strict_mode=True,
            )

    def test_tiktok_executor_strict_mode_blocks_search_keyword_fallback(self):
        session = FakeSession()
        executor = TikTokAdsExecutor(
            {"access_token": "tok", "advertiser_id": "adv-1"},
            session=session,
        )
        with self.assertRaises(ValueError):
            executor.apply_targeting(
                make_insight(),
                adgroup_id="100200300",
                strict_mode=True,
            )

    def test_linkedin_executor_strict_mode_requires_explicit_targeting_payload(self):
        session = FakeSession()
        executor = LinkedInAdsExecutor({"access_token": "tok"}, session=session)
        with self.assertRaises(ValueError):
            executor.apply_targeting(
                make_insight(),
                campaign_urn="urn:li:sponsoredCampaign:123",
                strict_mode=True,
            )


if __name__ == "__main__":
    unittest.main()
