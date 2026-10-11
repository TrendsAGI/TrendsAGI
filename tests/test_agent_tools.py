import json
import os
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from unittest.mock import MagicMock

import pytest

from trendsagi import TrendsAGIClient, TrendsAGITools, exceptions


TRENDS_PAYLOAD = {
    "trends": [{"id": 7, "name": "AI chips", "volume": 1200, "category": "Technology"}],
    "total": 1,
}


def _tools(allow_writes=False):
    client = TrendsAGIClient(api_key="test-key", base_url="http://unused.invalid")
    client._request = MagicMock(return_value=TRENDS_PAYLOAD)
    return client, TrendsAGITools(client, allow_writes=allow_writes)


def test_read_only_by_default():
    _, tools = _tools()
    assert "add_to_watchlist" not in tools.names
    assert "update_recommendation" not in tools.names
    assert "list_trends" in tools.names

    _, writable = _tools(allow_writes=True)
    assert {"add_to_watchlist", "update_recommendation"} <= set(writable.names)


def test_wire_formats_share_one_contract():
    _, tools = _tools()
    openai = {t["function"]["name"]: t["function"]["parameters"] for t in tools.openai()}
    responses = {t["name"]: t["parameters"] for t in tools.openai_responses()}
    anthropic = {t["name"]: t["input_schema"] for t in tools.anthropic()}
    assert openai == responses == anthropic
    for schema in openai.values():
        assert schema["type"] == "object"
        assert schema["additionalProperties"] is False


def test_list_trends_forwards_category_and_search_filters():
    client, tools = _tools()
    result = tools.call("list_trends", json.dumps({"category": "Technology", "search": "chips", "limit": 500}))

    assert result["result"]["trends"][0]["name"] == "AI chips"
    method, path = client._request.call_args.args
    params = client._request.call_args.kwargs["params"]
    assert (method, path) == ("GET", "/api/trends")
    assert params["category"] == "Technology"
    assert params["search"] == "chips"
    assert params["sort_by"] == "velocity"
    assert params["limit"] == 25  # clamped to the agent-safe maximum


def test_call_reports_errors_instead_of_raising():
    client, tools = _tools()
    assert "unknown tool" in tools.call("drop_tables")["error"]
    assert "missing required" in tools.call("get_trend", {})["error"]
    assert "unexpected arguments" in tools.call("get_trend", {"trend_id": 1, "sql": "x"})["error"]
    assert "not valid JSON" in tools.call("get_trend", "{nope")["error"]

    client._request.side_effect = exceptions.RateLimitError(429, "slow down")
    result = tools.call("list_trends", {})
    assert result["error"] == "rate_limited"
    assert "get_api_usage" in result["hint"]


def test_write_tool_is_unavailable_without_opt_in():
    client, tools = _tools()
    assert "unknown tool" in tools.call("add_to_watchlist", {"keyword": "x", "alert_condition_type": "volume_threshold"})["error"]
    client._request.assert_not_called()


class _FakeAPI(BaseHTTPRequestHandler):
    def do_GET(self):  # noqa: N802 - http.server naming
        if self.headers.get("X-API-Key") != "mcp-test-key":
            self.send_response(401)
            self.end_headers()
            return
        body = json.dumps(TRENDS_PAYLOAD).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


@pytest.mark.skipif(sys.version_info < (3, 10), reason="the MCP extra needs Python 3.10+")
def test_mcp_server_end_to_end():
    mcp = pytest.importorskip("mcp")
    import anyio
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    api = HTTPServer(("127.0.0.1", 0), _FakeAPI)
    threading.Thread(target=api.serve_forever, daemon=True).start()
    try:
        params = StdioServerParameters(
            command=sys.executable,
            args=["-m", "trendsagi.cli", "mcp", "--base-url", f"http://127.0.0.1:{api.server_port}"],
            env={**os.environ, "TRENDSAGI_API_KEY": "mcp-test-key"},
        )

        async def scenario():
            async with stdio_client(params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    listed = await session.list_tools()
                    names = {tool.name for tool in listed.tools}
                    assert "list_trends" in names and "add_to_watchlist" not in names
                    called = await session.call_tool("list_trends", {"category": "Technology"})
                    return json.loads(called.content[0].text)

        result = anyio.run(scenario)
        assert result["result"]["trends"][0]["name"] == "AI chips"
    finally:
        api.shutdown()
