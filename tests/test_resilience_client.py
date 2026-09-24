import json
import unittest
from unittest.mock import Mock, patch
import requests
from trendsagi import TrendsAGIClient, exceptions, models

def event():
    return dict(id=1,user_id=7,title="Review report",summary="Impact unconfirmed",severity="LOW",status="active",
        detected_at="2026-09-24T10:00:00Z",created_at="2026-09-24T10:00:00Z",updated_at="2026-09-24T10:00:00Z")
def response(code,payload=None,text=None):
    value=Mock(status_code=code,headers={})
    value.json.return_value=payload
    value.text=text if text is not None else json.dumps(payload)
    return value
class ResilienceClientTests(unittest.TestCase):
    def setUp(self):
        self.client=TrendsAGIClient("fixture-key",timeout=7)
        self.session=Mock()
        self.client._session=self.session

    def test_create_interest_selects_newest_matching_result(self):
        def interest(id, keyword):
            return dict(id=id,user_id=7,keyword=keyword,alert_condition_type='volume_threshold',created_at='2026-09-24T10:00:00Z')
        self.session.request.return_value=response(201,[interest(1,'paid media'),interest(8,'earthquake'),interest(3,'earthquake')])
        self.assertEqual(self.client.create_topic_interest('earthquake','volume_threshold').id,8)
        for payload in ([],[interest(1,'paid media')]):
            self.session.request.return_value=response(201,payload)
            with self.assertRaises(exceptions.TrendsAGIError):
                self.client.create_topic_interest('earthquake','volume_threshold')

    def test_legacy_event_and_additive_evidence(self):
        legacy=models.CrisisEvent.model_validate(event())
        self.assertEqual(legacy.source_refs,[])
        payload=event()
        payload.update(evidence_version="a"*32,freshness="fresh",review_status="unconfirmed",
            evidence_completeness={"score":75,"method":"resilience_evidence_completeness_v1"},
            source_refs=[dict(id=1,source_id="usgs",reference_id="test",source_url="https://earthquake.usgs.gov/test",
            observed_at="2026-09-24T10:00:00Z",retrieved_at="2026-09-24T10:01:00Z",excerpt="Report",claim="Source report",content_hash="hash")])
        self.session.request.return_value=response(200,payload)
        parsed=self.client.get_crisis_evidence(1)
        self.assertEqual(parsed.source_refs[0].source_id,"usgs")
        self.assertEqual(parsed.evidence_completeness.score,75)
        self.assertEqual(self.session.request.call_args.kwargs["timeout"],7)

    def test_review_and_exports(self):
        self.session.request.return_value=response(201,event())
        self.client.review_crisis_event(1,"unconfirmed","Need further context","a"*32)
        self.assertEqual(self.session.request.call_args.kwargs["json"]["evidence_version"],"a"*32)
        self.session.request.return_value=response(200,None,"<!doctype html><p>Snapshot</p>")
        self.assertIn("Snapshot",self.client.export_crisis_event(1,"html"))
        self.assertNotIn("_return_text",self.session.request.call_args.kwargs)
        with self.assertRaises(ValueError):self.client.export_crisis_event(1,"pdf")

    def test_sources_and_settings(self):
        self.session.request.return_value=response(200,{"sources":[]})
        self.assertEqual(self.client.get_resilience_sources().sources,[])
        self.session.request.return_value=response(200,{"location_query":"England"})
        self.assertEqual(self.client.set_resilience_location("England").location_query,"England")
        self.assertEqual(self.session.request.call_args.args[0],"PUT")

    def test_errors_are_compatible(self):
        for status,payload,error in [
            (401,{"detail":"Invalid key"},exceptions.AuthenticationError),
            (403,{"error":"Feature not available"},exceptions.AuthorizationError),
            (409,{"detail":"Evidence changed"},exceptions.ConflictError),
            (503,{"code":"CAPABILITY_UNAVAILABLE","detail":"Unavailable"},exceptions.CapabilityUnavailableError),
            (503,{"detail":"Maintenance"},exceptions.MaintenanceError),
        ]:
            with self.subTest(status=status,payload=payload):
                self.session.request.return_value=response(status,payload)
                with self.assertRaises(error):self.client.get_crisis_evidence(1)
        self.assertTrue(issubclass(exceptions.CapabilityUnavailableError,exceptions.MaintenanceError))
        self.assertTrue(issubclass(exceptions.AuthorizationError,exceptions.APIError))

    def test_transport_and_malformed_response(self):
        self.session.request.side_effect=requests.Timeout("bounded")
        with self.assertRaises(exceptions.TrendsAGIError):self.client.get_crisis_evidence(1)
        self.session.request.side_effect=None
        bad=response(200);bad.json.side_effect=ValueError("bad")
        self.session.request.return_value=bad
        with self.assertRaisesRegex(exceptions.TrendsAGIError,"malformed JSON"):self.client.get_crisis_evidence(1)

    def test_rate_limit_retry_is_bounded(self):
        self.client._enable_retry_on_rate_limit=True
        self.client._max_retries=1
        limited=response(429,{"detail":"Slow down"});limited.headers={"Retry-After":"0"}
        self.session.request.side_effect=[limited,limited]
        with patch("trendsagi.client.time.sleep"):
            with self.assertRaises(exceptions.RateLimitError):self.client.get_crisis_evidence(1)
        self.assertEqual(self.session.request.call_count,2)

    def test_list_filters_use_backend_period(self):
        self.session.request.return_value=response(200,{"events":[],"meta":{"total":0,"limit":10,"offset":0}})
        self.client.get_crisis_events(time_range="7d",freshness="fresh",source="usgs",location="Turkey")
        params=self.session.request.call_args.kwargs["params"]
        self.assertEqual(params["period"],"7d")
        self.assertEqual(params["source"],"usgs")
