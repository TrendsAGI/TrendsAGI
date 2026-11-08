from unittest.mock import MagicMock

import pytest

from trendsagi import TrendsAGIClient, TrendsAGITools, exceptions


def _client():
    client = TrendsAGIClient(api_key="test-key", base_url="http://unused.invalid")
    client._request = MagicMock()
    return client


def test_dossier_and_social_evidence_reads_return_none_on_404():
    client = _client()
    client._request.side_effect = exceptions.NotFoundError(404, "not found")
    assert client.get_trend_dossier(7) is None
    assert client.get_social_evidence(7) is None


def test_deep_dive_and_social_evidence_bodies():
    client = _client()
    client._request.return_value = {"trend_id": 7, "status": "complete"}

    client.enrich_trend(7, modules=["search_demand"], region="UK")
    method, path = client._request.call_args.args
    assert (method, path) == ("POST", "/api/trends/7/enrich")
    assert client._request.call_args.kwargs["json"] == {
        "modules": ["search_demand"],
        "region": "UK",
        "force": False,
    }

    client.run_social_evidence(7, modules=["posts"], force=True, request_id="req-1")
    method, path = client._request.call_args.args
    assert (method, path) == ("POST", "/api/trends/7/social-evidence")
    assert client._request.call_args.kwargs["json"] == {
        "modules": ["posts"],
        "region": "US",
        "force": True,
        "request_id": "req-1",
    }


def test_new_reads_use_the_documented_paths():
    client = _client()
    client._request.return_value = {
        "trend_id": 7,
        "status": "complete",
        "discoveries": [],
        "series": [],
        "related": [],
        "creators": [],
        "brands": [],
        "citations": [],
        "answer": "",
    }

    client.get_trend_discoveries(limit=500)
    assert client._request.call_args.kwargs["params"] == {"limit": 200}

    client.get_search_demand(7, geo="UK")
    assert client._request.call_args.args == ("GET", "/api/trends/7/search-demand")
    assert client._request.call_args.kwargs["params"] == {"geo": "UK"}

    client.get_brand_momentum(7, window="30d")
    assert client._request.call_args.args == ("GET", "/api/trends/7/brand-momentum")
    assert client._request.call_args.kwargs["params"] == {"window": "30d"}

    client.get_trend_creators(7)
    assert client._request.call_args.args == ("GET", "/api/trends/7/creators")

    client.ask_trend(7, "What should we do next?")
    assert client._request.call_args.args == ("POST", "/api/trends/7/ask")
    assert client._request.call_args.kwargs["json"] == {"question": "What should we do next?"}

    client.get_social_evidence_credits()
    assert client._request.call_args.args == ("GET", "/api/user/social-evidence-credits")


def test_agent_tools_gate_credit_spending():
    client = _client()
    read_only = TrendsAGITools(client)
    assert "get_trend_dossier" in read_only.names
    assert "get_social_evidence" in read_only.names
    assert "get_social_evidence_credits" in read_only.names
    assert "enrich_trend" not in read_only.names
    assert "run_social_evidence" not in read_only.names
    assert "create_social_evidence_checkout" not in read_only.names

    writable = TrendsAGITools(client, allow_writes=True)
    assert {"enrich_trend", "run_social_evidence", "create_social_evidence_checkout"} <= set(writable.names)
    annotations = {tool["name"]: tool["annotations"] for tool in writable.webmcp()}
    assert annotations["get_trend_dossier"]["readOnlyHint"] is True
    assert annotations["run_social_evidence"]["readOnlyHint"] is False


def test_ask_trend_rejects_an_empty_question():
    client = _client()
    with pytest.raises(ValueError):
        client.ask_trend(7, "  ")
