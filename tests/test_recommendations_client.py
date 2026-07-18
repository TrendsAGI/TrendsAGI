import unittest
from unittest.mock import Mock

from trendsagi import TrendsAGIClient


def recommendation_payload(include_brief=True, source_trend_id="123"):
    recommendation = {
        "id": 42,
        "user_id": 7,
        "type": "marketing_angle",
        "title": "Test a barrier-repair angle",
        "details": "Use the current measured signal to test a specific campaign angle.",
        "source_trend_id": source_trend_id,
        "source_trend_name": "Barrier repair skincare",
        "priority": "high",
        "status": "new",
        "created_at": "2026-07-18T09:00:00Z",
        "updated_at": "2026-07-18T09:00:00Z",
        "user_feedback": None,
    }
    if include_brief:
        recommendation["decision_brief"] = {
            "why_now": "Activity is accelerating while the latest signal is fresh.",
            "evidence": [
                {
                    "metric": "volume",
                    "label": "Current signal volume",
                    "value": 1200,
                    "unit": "signals",
                    "interpretation": "gaining activity",
                    "source": "trend_snapshots",
                    "source_url": "/trends/123/insights",
                    "observed_at": "2026-07-18T08:30:00Z",
                }
            ],
            "confidence": {
                "score": 85,
                "level": "high",
                "method": "evidence_completeness_v1",
                "reasons": ["The latest snapshot is fresh."],
                "missing_signals": [],
            },
            "expected_benefit": {
                "outcome": "Validate a campaign angle against current demand.",
                "basis": "A fresh, accelerating source trend.",
                "measurement": "Compare click-through rate against the current control.",
            },
            "urgency": {
                "level": "act_now",
                "window": "Next 24 hours",
                "reason": "Momentum is currently accelerating.",
            },
            "next_steps": [
                "Review the source trend.",
                "Run a bounded creative test against the current control.",
            ],
            "data_quality": {
                "status": "strong",
                "freshness": "fresh",
                "snapshot_at": "2026-07-18T08:30:00Z",
                "evidence_count": 8,
                "missing_signals": [],
            },
            "actionable": True,
        }
    return {
        "recommendations": [recommendation],
        "meta": {"total": 1, "limit": 10, "offset": 0},
    }


class RecommendationClientTests(unittest.TestCase):
    def make_client(self, payload):
        client = TrendsAGIClient(api_key="test-key", base_url="https://api.test.local")
        client._request = Mock(return_value=payload)
        return client

    def test_get_recommendations_parses_decision_brief(self):
        client = self.make_client(recommendation_payload())

        response = client.get_recommendations()

        recommendation = response.recommendations[0]
        self.assertEqual(recommendation.source_trend_id, "123")
        self.assertIsNotNone(recommendation.decision_brief)
        self.assertEqual(recommendation.decision_brief.confidence.score, 85)
        self.assertEqual(
            recommendation.decision_brief.confidence.method,
            "evidence_completeness_v1",
        )
        self.assertEqual(recommendation.decision_brief.evidence[0].value, 1200)
        self.assertTrue(recommendation.decision_brief.actionable)

    def test_legacy_response_without_brief_and_integer_trend_id_is_valid(self):
        client = self.make_client(
            recommendation_payload(include_brief=False, source_trend_id=123)
        )

        recommendation = client.get_recommendations().recommendations[0]

        self.assertEqual(recommendation.source_trend_id, 123)
        self.assertIsNone(recommendation.decision_brief)

    def test_default_filters_match_api_contract(self):
        client = self.make_client(recommendation_payload())

        client.get_recommendations()

        client._request.assert_called_once_with(
            "GET",
            "/api/intelligence/recommendations",
            params={
                "limit": 10,
                "offset": 0,
                "status": "new",
                "match_user_interests": "false",
                "sort": "priority",
            },
        )

    def test_filters_are_serialized_and_limit_is_capped(self):
        client = self.make_client(recommendation_payload())

        client.get_recommendations(
            limit=250,
            offset=20,
            recommendation_type="monitoring",
            source_trend_query="  skincare  ",
            priority="HIGH",
            status="VIEWED",
            match_user_interests=True,
            sort="NEWEST",
        )

        params = client._request.call_args.kwargs["params"]
        self.assertEqual(
            params,
            {
                "limit": 100,
                "offset": 20,
                "type": "monitoring",
                "sourceTrendQ": "skincare",
                "priority": "high",
                "status": "viewed",
                "match_user_interests": "true",
                "sort": "newest",
            },
        )

    def test_invalid_filter_values_fail_before_network_call(self):
        client = self.make_client(recommendation_payload())

        with self.assertRaisesRegex(ValueError, "sort must be priority or newest"):
            client.get_recommendations(sort="popular")
        with self.assertRaisesRegex(ValueError, "limit must be a positive integer"):
            client.get_recommendations(limit=0)

        client._request.assert_not_called()

    def test_recommendation_action_is_normalized_and_parsed(self):
        client = self.make_client(recommendation_payload()["recommendations"][0])

        recommendation = client.perform_recommendation_action(42, action=" VIEWED ")

        self.assertEqual(recommendation.id, 42)
        client._request.assert_called_once_with(
            "POST",
            "/api/intelligence/recommendations/42/action",
            json={"action": "viewed"},
        )

    def test_invalid_recommendation_action_fails_before_network_call(self):
        client = self.make_client(recommendation_payload()["recommendations"][0])

        with self.assertRaisesRegex(ValueError, "unsupported recommendation action"):
            client.perform_recommendation_action(42, action="launched")
        with self.assertRaisesRegex(ValueError, "500 characters or fewer"):
            client.perform_recommendation_action(42, feedback="x" * 501)
        with self.assertRaisesRegex(ValueError, "positive integer"):
            client.perform_recommendation_action(0, action="viewed")

        client._request.assert_not_called()


if __name__ == "__main__":
    unittest.main()
