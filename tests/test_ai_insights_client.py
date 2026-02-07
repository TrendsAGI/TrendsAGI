import json
import unittest

from trendsagi import TrendsAGIClient


class DummyResponse:
    def __init__(self, status_code, payload):
        self.status_code = status_code
        self._payload = payload
        self.headers = {}
        self.text = json.dumps(payload) if payload is not None else "null"
        self.content = self.text.encode("utf-8")

    def json(self):
        return self._payload


class FakeSession:
    def __init__(self, routes):
        self.routes = routes
        self.headers = {}
        self.calls = []

    def request(self, method, url, **kwargs):
        self.calls.append((method, url, kwargs))
        key = (method.upper(), url)
        if key not in self.routes:
            return DummyResponse(404, {"detail": "not found"})
        return self.routes[key]


class AIInsightClientTests(unittest.TestCase):
    def test_get_ai_insights_returns_typed_model(self):
        base_url = "https://api.test.local"
        trend_id = 123
        payload = {
            "trend_id": trend_id,
            "sentiment_category": "positive",
            "key_themes": ["fitness"],
            "trend_metrics": {"commercial_intent": 0.88},
            "audience_injection": {"interest_keywords": ["running shoes"]},
        }
        session = FakeSession(
            {
                ("GET", f"{base_url}/api/trends/{trend_id}/ai-insights"): DummyResponse(200, payload),
            }
        )

        client = TrendsAGIClient(api_key="test-key", base_url=base_url)
        client._session = session
        insight = client.get_ai_insights(trend_id)

        self.assertIsNotNone(insight)
        self.assertEqual(insight.trend_id, trend_id)
        self.assertEqual(insight.sentiment_category, "positive")
        self.assertEqual(insight.trend_metrics.commercial_intent, 0.88)
        self.assertEqual(insight.audience_injection.interest_keywords, ["running shoes"])

    def test_generate_and_status_roundtrip_models(self):
        base_url = "https://api.test.local"
        trend_id = 7
        task_id = "task-xyz"
        session = FakeSession(
            {
                ("POST", f"{base_url}/api/trends/{trend_id}/ai-insights/generate"): DummyResponse(
                    200, {"task_id": task_id, "status": "queued", "message": "ok"}
                ),
                ("GET", f"{base_url}/api/trends/ai-insights/status/{task_id}"): DummyResponse(
                    200, {"status": "SUCCESS"}
                ),
            }
        )

        client = TrendsAGIClient(api_key="test-key", base_url=base_url)
        client._session = session

        queued = client.generate_ai_insights(trend_id, force_refresh=True)
        self.assertEqual(queued.task_id, task_id)
        self.assertEqual(queued.status, "queued")

        status = client.get_ai_insight_status(task_id)
        self.assertEqual(status.status, "SUCCESS")


if __name__ == "__main__":
    unittest.main()

