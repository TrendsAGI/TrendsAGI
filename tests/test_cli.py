import json
import os
import re
import stat
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import pytest

from trendsagi import cli

KEY = "ltc_live_testkey"


class _Recorder(BaseHTTPRequestHandler):
    """Records each request and answers from the server's route table."""

    def _handle(self):
        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length) if length else b""
        path, _, query = self.path.partition("?")
        self.server.calls.append({
            "method": self.command,
            "path": path,
            "query": dict(p.split("=", 1) for p in query.split("&") if p),
            "body": json.loads(raw) if raw else None,
            "headers": dict(self.headers),
        })
        status, payload, content_type = self.server.routes.get(
            (self.command, path), (200, {"ok": True}, "application/json")
        )
        if callable(payload):
            payload = payload()
        body = payload if isinstance(payload, bytes) else json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    do_GET = do_POST = do_PUT = do_PATCH = do_DELETE = _handle

    def log_message(self, *args):
        pass


@pytest.fixture
def api(monkeypatch, tmp_path):
    server = HTTPServer(("127.0.0.1", 0), _Recorder)
    server.calls, server.routes = [], {}
    threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True).start()
    monkeypatch.setenv("TRENDSAGI_BASE_URL", f"http://127.0.0.1:{server.server_port}")
    monkeypatch.setenv("TRENDSAGI_CONFIG", str(tmp_path / "config.json"))
    monkeypatch.delenv("TRENDSAGI_API_KEY", raising=False)
    yield server
    server.shutdown()


def run(capsys, *argv):
    code = cli.main(list(argv))
    out, err = capsys.readouterr()
    return code, out, err


def test_every_path_placeholder_has_an_argument():
    def walk(commands):
        for cmd in commands:
            if "commands" in cmd:
                yield from walk(cmd["commands"])
            else:
                yield cmd

    spec = cli.load_spec()
    commands = list(walk(spec["commands"]))
    assert len(commands) > 50
    for cmd in commands:
        if "path" not in cmd:
            assert cmd.get("handler"), cmd["name"]
            continue
        assert cmd["method"] in {"GET", "POST", "PUT", "PATCH", "DELETE"}
        names = {a["name"] for a in cmd.get("args", [])}
        for placeholder in re.findall(r"{(\w+)}", cmd["path"]):
            assert placeholder in names, (cmd["path"], placeholder)
        if cmd.get("handler"):
            assert cmd["handler"] in cli.HANDLERS
    cli.build_parser(spec)


def test_trends_list_sends_query_key_and_cli_user_agent(api, capsys, monkeypatch):
    monkeypatch.setenv("TRENDSAGI_API_KEY", KEY)
    api.routes[("GET", "/api/trends")] = (200, {"trends": [{"id": 7, "name": "AI chips"}]}, "application/json")

    code, out, _ = run(capsys, "trends", "list", "--category", "Technology", "--sort", "velocity", "--watchlist")

    assert code == 0
    assert json.loads(out)["trends"][0]["id"] == 7  # not a terminal, so JSON
    call = api.calls[0]
    assert call["query"] == {"category": "Technology", "sort_by": "velocity", "limit": "20", "for_user_interests": "true"}
    assert call["headers"]["X-API-Key"] == KEY
    assert call["headers"]["User-Agent"].startswith("trendsagi-cli/")


def test_not_logged_in_exits_4_without_a_request(api, capsys):
    code, _, err = run(capsys, "trends", "list")
    assert code == cli.EXIT_AUTH
    assert "trendsagi login" in err
    assert api.calls == []


def test_public_commands_skip_the_api_key(api, capsys, monkeypatch):
    code, _, _ = run(capsys, "status")
    assert code == 0
    monkeypatch.setenv("TRENDSAGI_API_KEY", KEY)
    run(capsys, "tools", "list")
    assert [c["path"] for c in api.calls] == ["/status", "/api/agent/tools"]
    assert all("X-API-Key" not in c["headers"] for c in api.calls)


def test_login_validates_and_saves_key_privately(api, capsys, monkeypatch, tmp_path):
    api.routes[("GET", "/api/user/profile")] = (200, {"email": "ana@example.com"}, "application/json")
    monkeypatch.setattr("sys.stdin", __import__("io").StringIO(KEY + "\n"))

    code, _, err = run(capsys, "login", "--with-token")

    assert code == 0
    assert "ana@example.com" in err
    path = tmp_path / "config.json"
    assert json.loads(path.read_text())["api_key"] == KEY
    if os.name != "nt":
        assert stat.S_IMODE(path.stat().st_mode) == 0o600
    assert api.calls[0]["headers"]["X-API-Key"] == KEY

    # The saved key is used by later commands, and logout forgets it.
    run(capsys, "usage")
    assert api.calls[-1]["headers"]["X-API-Key"] == KEY
    code, _, _ = run(capsys, "logout")
    assert code == 0
    assert "api_key" not in json.loads(path.read_text())


def test_login_rejects_text_that_is_not_an_api_key(api, capsys, monkeypatch):
    monkeypatch.setattr("sys.stdin", __import__("io").StringIO("hunter2\n"))
    code, _, err = run(capsys, "login", "--with-token")
    assert code == cli.EXIT_USAGE
    assert "ltc_live_" in err
    assert api.calls == []


def test_flag_beats_env_beats_saved_key(api, capsys, monkeypatch, tmp_path):
    (tmp_path / "config.json").write_text(json.dumps({"api_key": "ltc_live_saved"}))
    run(capsys, "usage")
    monkeypatch.setenv("TRENDSAGI_API_KEY", "ltc_live_env")
    run(capsys, "usage")
    run(capsys, "--api-key", "ltc_live_flag", "usage")
    run(capsys, "usage", "--api-key", "ltc_live_flag2")
    assert [c["headers"]["X-API-Key"] for c in api.calls] == [
        "ltc_live_saved", "ltc_live_env", "ltc_live_flag", "ltc_live_flag2",
    ]


def test_destructive_commands_need_yes_without_a_terminal(api, capsys, monkeypatch):
    monkeypatch.setenv("TRENDSAGI_API_KEY", KEY)
    code, _, err = run(capsys, "webhooks", "delete", "5")
    assert code == cli.EXIT_USAGE
    assert "--yes" in err
    assert api.calls == []

    api.routes[("DELETE", "/api/integrations/webhooks/5")] = (204, b"", "application/json")
    code, _, _ = run(capsys, "webhooks", "delete", "5", "--yes")
    assert code == 0
    assert api.calls[0]["method"] == "DELETE"


def test_ads_apply_body_and_confirmation_names_the_platform(api, capsys, monkeypatch):
    monkeypatch.setenv("TRENDSAGI_API_KEY", KEY)
    code, _, err = run(capsys, "ads", "apply", "meta_ads", "--trend", "9", "--level", "ad")
    assert code == cli.EXIT_USAGE and "meta_ads" in err

    run(capsys, "-y", "ads", "apply", "meta_ads", "--trend", "9", "--level", "ad", "--strict-safety", "false")
    call = api.calls[0]
    assert call["path"] == "/api/integrations/ads/meta_ads/apply"
    assert call["body"] == {"trend_id": 9, "apply_level": "ad", "strict_safety": False}


def test_nested_body_fields_and_data_merge(api, capsys, monkeypatch):
    monkeypatch.setenv("TRENDSAGI_API_KEY", KEY)
    run(
        capsys, "ads", "report", "tiktok_ads", "--level", "campaign", "--start", "2026-10-01",
        "--end", "2026-10-07", "--account", "acc1", "--fields", "spend, clicks",
        "--data", '{"template_id": "custom", "level": "ad"}',
    )
    assert api.calls[0]["body"] == {
        "platform": "tiktok_ads",
        "template_id": "custom",
        "level": "campaign",
        "date_range": {"start_date": "2026-10-01", "end_date": "2026-10-07"},
        "scope": {"account_id": "acc1"},
        "fields": ["spend", "clicks"],
    }


def test_watchlist_add_needs_a_keyword_or_category(api, capsys, monkeypatch):
    monkeypatch.setenv("TRENDSAGI_API_KEY", KEY)
    code, _, _ = run(capsys, "watchlist", "add")
    assert code == cli.EXIT_USAGE
    run(capsys, "watchlist", "add", "--category", "Beauty", "--repeat", "--growth", "25")
    assert api.calls[0]["body"] == {
        "category": "Beauty", "alert_behavior": "notify_repeating", "percentage_growth_value": 25.0,
    }


def test_sql_refusal_prints_code_and_hint(api, capsys, monkeypatch):
    monkeypatch.setenv("TRENDSAGI_API_KEY", KEY)
    api.routes[("POST", "/api/agent/sql")] = (
        400,
        {"error": "unknown_table", "detail": "saas_users is not available", "hint": "See trendsagi schema."},
        "application/json",
    )
    code, _, err = run(capsys, "sql", "SELECT * FROM saas_users")
    assert code == 1
    assert "unknown_table" in err and "See trendsagi schema." in err
    assert api.calls[0]["body"] == {"query": "SELECT * FROM saas_users"}


def test_tools_call_unwraps_the_text_result(api, capsys, monkeypatch):
    monkeypatch.setenv("TRENDSAGI_API_KEY", KEY)
    api.routes[("POST", "/api/agent/tools/list_trends")] = (
        200, {"content": [{"type": "text", "text": '{"trends": [1]}'}], "isError": False}, "application/json",
    )
    code, out, _ = run(capsys, "tools", "call", "list_trends", "--args", '{"limit": 5}', "-a", "category=Tech", "-a", "offset=10")
    assert code == 0
    assert json.loads(out) == {"trends": [1]}
    assert api.calls[0]["body"] == {"limit": 5, "category": "Tech", "offset": 10}

    api.routes[("POST", "/api/agent/tools/list_trends")] = (
        200, {"content": [{"type": "text", "text": '{"error": "http_403"}'}], "isError": True}, "application/json",
    )
    code, _, err = run(capsys, "tools", "call", "list_trends")
    assert code == 1 and "http_403" in err


def test_api_command_builds_any_request(api, capsys, monkeypatch):
    monkeypatch.setenv("TRENDSAGI_API_KEY", KEY)
    run(capsys, "api", "/api/trends", "-q", "limit=2")
    run(capsys, "api", "api/user/interests", "-f", "keyword=solar", "-f", "volume_threshold_value=500")
    run(capsys, "api", "/api/user/interests/3", "-X", "delete")
    assert [(c["method"], c["path"]) for c in api.calls] == [
        ("GET", "/api/trends"), ("POST", "/api/user/interests"), ("DELETE", "/api/user/interests/3"),
    ]
    assert api.calls[0]["query"] == {"limit": "2"}
    assert api.calls[1]["body"] == {"keyword": "solar", "volume_threshold_value": 500}


def test_report_export_writes_raw_csv(api, capsys, monkeypatch, tmp_path):
    monkeypatch.setenv("TRENDSAGI_API_KEY", KEY)
    api.routes[("POST", "/api/integrations/ads/reporting/export")] = (200, b"date,spend\n2026-10-01,5\n", "text/csv")
    target = tmp_path / "report.csv"
    code, _, _ = run(
        capsys, "ads", "report-export", "google_ads", "--level", "ad", "--start", "2026-10-01",
        "--end", "2026-10-02", "--account", "1", "-o", str(target),
    )
    assert code == 0
    assert target.read_bytes() == b"date,spend\n2026-10-01,5\n"
    assert "out" not in api.calls[0]["body"]


def test_insights_generate_wait_polls_then_prints_insights(api, capsys, monkeypatch):
    monkeypatch.setenv("TRENDSAGI_API_KEY", KEY)
    monkeypatch.setattr(cli.time, "sleep", lambda _: None)
    states = iter(["PROCESSING", "SUCCESS"])
    api.routes[("POST", "/api/trends/12/ai-insights/generate")] = (200, {"task_id": "t1", "status": "queued"}, "application/json")
    api.routes[("GET", "/api/trends/ai-insights/status/t1")] = (200, lambda: {"status": next(states)}, "application/json")
    api.routes[("GET", "/api/trends/12/ai-insights")] = (200, {"trend_id": 12, "summary": "x"}, "application/json")

    code, out, _ = run(capsys, "insights", "generate", "12", "--wait", "--force-refresh")

    assert code == 0
    assert json.loads(out)["trend_id"] == 12
    assert api.calls[0]["body"] == {"force_refresh": True}
    assert [c["path"] for c in api.calls][1:] == [
        "/api/trends/ai-insights/status/t1", "/api/trends/ai-insights/status/t1", "/api/trends/12/ai-insights",
    ]


def test_invalid_key_exits_4(api, capsys, monkeypatch):
    monkeypatch.setenv("TRENDSAGI_API_KEY", KEY)
    api.routes[("GET", "/api/user/api-usage")] = (401, {"detail": "Invalid or expired API key"}, "application/json")
    code, _, err = run(capsys, "usage")
    assert code == cli.EXIT_AUTH
    assert "Invalid or expired API key" in err


def test_table_rendering():
    rows = [{"id": 1, "name": "AI chips", "volume": 1200, "growth": 12.5, "tags": ["a", "b"], "nested": {"x": 1}}]
    table = cli.render_table(rows, ["id", "name", "growth", "missing"])
    header, line = table.splitlines()
    assert header.split() == ["ID", "NAME", "GROWTH"]
    assert line.split() == ["1", "AI", "chips", "12.5"]
    assert cli.render_table([], ["id"]) == "No results."
    # With no known columns, scalar fields are picked automatically.
    assert "VOLUME" in cli.render_table(rows, ["unknown"])


def test_npm_package_ships_the_same_spec():
    npm_spec = Path(__file__).resolve().parents[1] / "npm" / "cli_spec.json"
    assert json.loads(npm_spec.read_text()) == cli.load_spec(), "run: cp src/trendsagi/cli_spec.json npm/"
