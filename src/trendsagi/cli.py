"""The ``trendsagi`` command line.

Every API command is declared in ``cli_spec.json``, which the npm package
(``npx trendsagi``) reads too, so both CLIs accept the same commands and
flags. This module turns the spec into argparse subcommands and requests;
commands that need more than one request or special output name a
``handler`` in the spec and are implemented here.

    trendsagi login
    trendsagi trends list --sort velocity --limit 10
    trendsagi sql "SELECT category, count(*) FROM trends GROUP BY 1"
"""

from __future__ import annotations

import argparse
import getpass
import json
import os
import platform
import shutil
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import quote

SPEC_PATH = Path(__file__).with_name("cli_spec.json")
DEFAULT_BASE_URL = "https://api.trendsagi.com"
API_KEY_PREFIXES = ("ltc_live_", "ltc_test_")
BODY_METHODS = {"POST", "PUT", "PATCH"}

EXIT_ERROR = 1
EXIT_USAGE = 2
EXIT_AUTH = 4

# Insight generation task states that mean the task is over.
_TASK_DONE = {"SUCCESS", "COMPLETED", "DONE"}
_TASK_FAILED = {"FAILURE", "FAILED", "ERROR"}


class CLIError(Exception):
    def __init__(self, message: str, code: int = EXIT_ERROR):
        super().__init__(message)
        self.code = code


def load_spec() -> Dict[str, Any]:
    return json.loads(SPEC_PATH.read_text(encoding="utf-8"))


def _version() -> str:
    from . import __version__

    return __version__


# --- saved login -------------------------------------------------------------


def config_path() -> Path:
    """Where ``trendsagi login`` keeps the API key (shared with the npm CLI)."""
    override = os.environ.get("TRENDSAGI_CONFIG")
    if override:
        return Path(override)
    if os.name == "nt":
        base = os.environ.get("APPDATA") or str(Path.home() / "AppData" / "Roaming")
    else:
        base = os.environ.get("XDG_CONFIG_HOME") or str(Path.home() / ".config")
    return Path(base) / "trendsagi" / "config.json"


def read_config() -> Dict[str, Any]:
    path = config_path()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}
    except (OSError, ValueError) as exc:
        raise CLIError(f"Could not read {path}: {exc}")
    return data if isinstance(data, dict) else {}


def write_config(data: Dict[str, Any]) -> Path:
    path = config_path()
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    tmp = path.with_name(path.name + ".tmp")
    fd = os.open(str(tmp), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2)
        fh.write("\n")
    os.replace(str(tmp), str(path))
    return path


class Context:
    """Resolved credentials and output settings for one invocation."""

    def __init__(self, args: argparse.Namespace, spec: Dict[str, Any]):
        self.spec = spec
        self.flag_api_key = getattr(args, "api_key", None)
        self._config: Optional[Dict[str, Any]] = None
        if self.flag_api_key:
            self.api_key, self.key_source = self.flag_api_key, "--api-key"
        elif os.environ.get("TRENDSAGI_API_KEY"):
            self.api_key, self.key_source = os.environ["TRENDSAGI_API_KEY"], "TRENDSAGI_API_KEY"
        else:
            self.api_key = self.config.get("api_key")
            self.key_source = str(config_path()) if self.api_key else None
        self.base_url = (
            getattr(args, "base_url", None)
            or os.environ.get("TRENDSAGI_BASE_URL")
            or self.config.get("base_url")
            or DEFAULT_BASE_URL
        ).rstrip("/")
        self.json = bool(getattr(args, "json", False))
        self.yes = bool(getattr(args, "yes", False))
        self.tty = sys.stdout.isatty()

    @property
    def config(self) -> Dict[str, Any]:
        if self._config is None:
            self._config = read_config()
        return self._config

    def client(self, auth: bool = True, api_key: Optional[str] = None):
        from .client import TrendsAGIClient

        key = api_key or self.api_key
        if auth and not key:
            raise CLIError(
                "Not logged in. Run 'trendsagi login' or set TRENDSAGI_API_KEY.\n"
                f"Create an API key at {self.spec['api_keys_url']}",
                EXIT_AUTH,
            )
        client = TrendsAGIClient(
            api_key=key or "anonymous",
            base_url=self.base_url,
            enable_retry_on_rate_limit=True,
            max_retries=2,
        )
        client._session.headers["User-Agent"] = (
            f"trendsagi-cli/{_version()} python/{platform.python_version()}"
        )
        return client

    def request(self, method: str, path: str, params=None, body=None, auth: bool = True, raw: bool = False):
        return self.client(auth=auth).request(method, path, params=params, json=body, auth=auth, raw=raw)


# --- argument parsing ----------------------------------------------------------


def _parse_bool(value: str) -> bool:
    lowered = value.strip().lower()
    if lowered in {"true", "1", "yes", "on"}:
        return True
    if lowered in {"false", "0", "no", "off"}:
        return False
    raise argparse.ArgumentTypeError(f"expected true or false, got {value!r}")


def _parse_json(value: str) -> Any:
    """JSON text, @file.json, or - for standard input."""
    if value == "-":
        text = sys.stdin.read()
    elif value.startswith("@"):
        try:
            text = Path(value[1:]).read_text(encoding="utf-8")
        except OSError as exc:
            raise argparse.ArgumentTypeError(f"cannot read {value[1:]}: {exc.strerror}")
    else:
        text = value
    try:
        return json.loads(text)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"invalid JSON: {exc}")


def _parse_list(value: str) -> List[str]:
    return [part.strip() for part in value.split(",") if part.strip()]


def _parse_pair(value: str) -> Tuple[str, Any]:
    key, sep, raw = value.partition("=")
    if not sep or not key:
        raise argparse.ArgumentTypeError(f"expected KEY=VALUE, got {value!r}")
    return key, raw


def _json_value(raw: str) -> Any:
    """Read a KEY=VALUE value as JSON when it is JSON (5, true, [1,2]), else as text."""
    try:
        return json.loads(raw)
    except ValueError:
        return raw


_TYPES = {
    "int": int,
    "float": float,
    "bool": _parse_bool,
    "json": _parse_json,
    "list": _parse_list,
    "pairs": _parse_pair,
}


_METAVARS = {"int": "N", "float": "NUMBER", "bool": "true|false", "json": "JSON", "list": "A,B"}


def _dest(prefix: str, name: str) -> str:
    return prefix + name.replace("-", "_")


def _add_common(parser: argparse.ArgumentParser) -> None:
    # SUPPRESS keeps a subcommand from overwriting a value given before it.
    group = parser.add_argument_group("global options")
    group.add_argument("--api-key", default=argparse.SUPPRESS, help="API key (default: $TRENDSAGI_API_KEY or the saved login).")
    group.add_argument("--base-url", default=argparse.SUPPRESS, help=f"API base URL (default: {DEFAULT_BASE_URL}).")
    group.add_argument("--json", action="store_true", default=argparse.SUPPRESS, help="Print raw JSON instead of tables.")
    group.add_argument("-y", "--yes", action="store_true", default=argparse.SUPPRESS, help="Do not ask before changing or deleting things.")


def _add_command(subparsers, cmd: Dict[str, Any]) -> None:
    parser = subparsers.add_parser(
        cmd["name"],
        aliases=cmd.get("aliases", []),
        help=cmd["help"],
        description=cmd["help"],
    )
    if "commands" in cmd:
        children = parser.add_subparsers(dest=_dest("cmd_", cmd["name"]), metavar="COMMAND")
        for child in cmd["commands"]:
            _add_command(children, child)
        parser.set_defaults(_group_parser=parser)
        return

    for arg in cmd.get("args", []):
        kwargs: Dict[str, Any] = {"help": arg.get("help")}
        if arg.get("type") in _TYPES:
            kwargs["type"] = _TYPES[arg["type"]]
        if arg.get("choices"):
            kwargs["choices"] = arg["choices"]
        if arg.get("optional"):
            kwargs["nargs"] = "?"
        parser.add_argument(_dest("arg_", arg["name"]), metavar=arg["name"], **kwargs)

    for opt in cmd.get("options", []):
        names = [f"--{opt['flag']}"]
        if opt.get("short"):
            names.insert(0, f"-{opt['short']}")
        kind = opt.get("type", "string")
        help_text = opt.get("help") or ""
        if opt.get("default") is not None and "default" not in help_text:
            help_text += f" (default {opt['default']})"
        kwargs = {"dest": _dest("opt_", opt["flag"]), "help": help_text}
        if kind == "flag":
            kwargs.update(action="store_const", const=opt.get("value", True), default=None)
        elif kind == "pairs":
            kwargs.update(action="append", type=_parse_pair, default=None)
        else:
            if kind in _TYPES:
                kwargs["type"] = _TYPES[kind]
            if opt.get("choices"):
                kwargs["choices"] = opt["choices"]
            kwargs["default"] = opt.get("default")
            kwargs["required"] = bool(opt.get("required"))
        if kind not in {"flag", "pairs"} and not opt.get("choices"):
            kwargs["metavar"] = opt.get("metavar") or _METAVARS.get(kind) or opt["flag"].upper().replace("-", "_")
        elif opt.get("metavar"):
            kwargs["metavar"] = opt["metavar"]
        parser.add_argument(*names, **kwargs)

    if cmd.get("data"):
        parser.add_argument(
            "-d", "--data", dest="opt_data", type=_parse_json, metavar="JSON",
            help="Request body as JSON, @file.json or - for standard input; flags override its fields.",
        )
    _add_common(parser)
    parser.set_defaults(_command=cmd)


def build_parser(spec: Optional[Dict[str, Any]] = None) -> argparse.ArgumentParser:
    spec = spec or load_spec()
    parser = argparse.ArgumentParser(
        prog="trendsagi",
        description=spec["description"],
        epilog=(
            "examples:\n"
            "  trendsagi login\n"
            "  trendsagi trends list --sort velocity --limit 10\n"
            "  trendsagi insights get 123\n"
            "  trendsagi sql \"SELECT category, count(*) FROM trends GROUP BY 1\"\n"
            "  trendsagi api /api/trends -q category=Technology\n\n"
            f"Docs: {spec['docs_url']}"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--version", action="version", version=f"trendsagi {_version()}")
    _add_common(parser)
    subparsers = parser.add_subparsers(dest="command", metavar="COMMAND")
    for cmd in spec["commands"]:
        _add_command(subparsers, cmd)

    mcp_parser = subparsers.add_parser(
        "mcp",
        help="Run the TrendsAGI MCP server over stdio for AI agents (needs trendsagi[mcp]).",
    )
    mcp_parser.add_argument(
        "--allow-writes",
        action="store_true",
        help="Also expose tools that change account state (watchlist, recommendation workflow).",
    )
    _add_common(mcp_parser)

    scaffold_parser = subparsers.add_parser(
        "scaffold",
        help="Copy customer-hosted integration templates to your current workspace.",
    )
    scaffold_parser.add_argument(
        "--type",
        dest="template_type",
        required=True,
        choices=["docker", "terraform"],
        help="Template bundle to copy.",
    )
    scaffold_parser.add_argument(
        "--output-dir",
        default=".",
        help="Target directory (defaults to current working directory).",
    )
    return parser


# --- requests ------------------------------------------------------------------


def _put(target: Dict[str, Any], dotted: str, value: Any) -> None:
    keys = dotted.split(".")
    for key in keys[:-1]:
        nested = target.get(key)
        if not isinstance(nested, dict):
            nested = target[key] = {}
        target = nested
    target[keys[-1]] = value


def _query_value(value: Any) -> Any:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, list):
        return ",".join(str(v) for v in value)
    return value


def build_request(cmd: Dict[str, Any], args: argparse.Namespace) -> Tuple[str, str, Dict[str, Any], Optional[Dict[str, Any]]]:
    """Return (method, path, query, body) for a spec command."""
    method = cmd["method"]
    path = cmd["path"]
    default_in = "body" if method in BODY_METHODS else "query"
    query: Dict[str, Any] = {}
    body: Dict[str, Any] = {}

    data = getattr(args, "opt_data", None)
    if data is not None:
        if not isinstance(data, dict):
            raise CLIError("--data must be a JSON object.", EXIT_USAGE)
        body.update(data)

    given = set()
    for arg in cmd.get("args", []):
        value = getattr(args, _dest("arg_", arg["name"]))
        if value is None:
            continue
        if arg.get("stdin") and value == "-":
            value = sys.stdin.read().strip()
        given.add(arg["name"])
        placeholder = "{" + arg["name"] + "}"
        where = arg.get("in") or ("path" if placeholder in path else default_in)
        if where == "path":
            path = path.replace(placeholder, quote(str(value), safe=""))
        else:
            _put(query if where == "query" else body, arg.get("param", arg["name"]), value)

    for opt in cmd.get("options", []):
        if opt.get("local"):
            continue
        value = getattr(args, _dest("opt_", opt["flag"]))
        if value is None:
            continue
        given.add(opt["flag"])
        where = opt.get("in") or default_in
        _put(query if where == "query" else body, opt.get("param", opt["flag"].replace("-", "_")), value)

    required = cmd.get("require_one_of")
    if required and not given.intersection(required):
        raise CLIError(f"Give one of: {', '.join(required)}.", EXIT_USAGE)

    query = {k: _query_value(v) for k, v in query.items()}
    return method, path, query, (body if method in BODY_METHODS else None)


def _confirm(ctx: Context, cmd: Dict[str, Any], args: argparse.Namespace) -> None:
    message = cmd.get("confirm")
    if not message or ctx.yes:
        return
    values = {arg["name"]: getattr(args, _dest("arg_", arg["name"])) for arg in cmd.get("args", [])}
    prompt = message.format(**values)
    if not sys.stdin.isatty():
        raise CLIError(f"{prompt} Pass --yes to confirm.", EXIT_USAGE)
    answer = input(f"{prompt} [y/N] ").strip().lower()
    if answer not in {"y", "yes"}:
        raise CLIError("Cancelled.", EXIT_ERROR)


# --- output --------------------------------------------------------------------


def print_json(data: Any) -> None:
    print(json.dumps(data, indent=2, ensure_ascii=False, default=str))


def _cell(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "yes" if value else "no"
    if isinstance(value, float):
        return str(int(value)) if value.is_integer() else f"{value:.2f}".rstrip("0").rstrip(".")
    if isinstance(value, list):
        return ", ".join(_cell(v) for v in value)
    if isinstance(value, dict):
        return json.dumps(value, ensure_ascii=False, default=str)
    return " ".join(str(value).split())


def _truncate(text: str, width: int) -> str:
    return text if len(text) <= width else text[: max(width - 1, 0)] + "…"


def render_table(rows: List[Dict[str, Any]], columns: Optional[List[str]] = None) -> str:
    if not rows:
        return "No results."
    present = [c for c in (columns or []) if any(isinstance(r, dict) and c in r for r in rows)]
    if not present:
        first = rows[0] if isinstance(rows[0], dict) else {}
        present = [k for k, v in first.items() if not isinstance(v, (dict, list))][:7]
    if not present:
        return json.dumps(rows, indent=2, ensure_ascii=False, default=str)
    cells = [[_cell(r.get(c)) if isinstance(r, dict) else "" for c in present] for r in rows]
    headers = [c.replace("_", " ").upper() for c in present]
    widths = [max(len(h), *(len(row[i]) for row in cells)) for i, h in enumerate(headers)]
    widths = [min(w, 60) for w in widths]
    budget = shutil.get_terminal_size((120, 20)).columns - 2 * (len(widths) - 1)
    while sum(widths) > budget and max(widths) > 10:
        widest = widths.index(max(widths))
        widths[widest] -= 1
    lines = ["  ".join(_truncate(h, w).ljust(w) for h, w in zip(headers, widths)).rstrip()]
    for row in cells:
        lines.append("  ".join(_truncate(c, w).ljust(w) for c, w in zip(row, widths)).rstrip())
    return "\n".join(lines)


def render_object(data: Dict[str, Any]) -> str:
    width = max((len(k) for k in data), default=0)
    lines = []
    for key, value in data.items():
        if value is None or value == [] or value == {}:
            continue
        lines.append(f"{key.ljust(width)}  {_truncate(_cell(value), 100)}")
    return "\n".join(lines)


def _rows_at(data: Any, path: str) -> Optional[List[Any]]:
    if path == "":
        return data if isinstance(data, list) else None
    if isinstance(data, dict):
        rows = data.get(path)
        return rows if isinstance(rows, list) else None
    if isinstance(data, list):
        return data
    return None


def emit(ctx: Context, cmd: Dict[str, Any], data: Any) -> None:
    if data is None:
        if ctx.tty and not ctx.json:
            print("Done.")
        return
    table = cmd.get("table")
    if ctx.json or not ctx.tty or not table:
        print_json(data)
        return
    if table.get("kind") == "object" and isinstance(data, dict):
        print(render_object(data))
        return
    rows = _rows_at(data, table.get("rows", ""))
    if rows is None:
        print_json(data)
        return
    summary = data.get(table["summary"]) if table.get("summary") and isinstance(data, dict) else None
    if isinstance(summary, dict):
        print(render_object(summary))
        print()
    print(render_table(rows, table.get("columns")))


# --- handlers ------------------------------------------------------------------


def run_spec_command(ctx: Context, cmd: Dict[str, Any], args: argparse.Namespace) -> int:
    method, path, query, body = build_request(cmd, args)
    _confirm(ctx, cmd, args)
    auth = cmd.get("auth", True)
    if cmd.get("output") == "raw":
        content = ctx.request(method, path, params=query, body=body, auth=auth, raw=True)
        out = getattr(args, "opt_out", None)
        if out:
            Path(out).write_bytes(content)
            print(f"Wrote {len(content)} bytes to {out}", file=sys.stderr)
        else:
            sys.stdout.buffer.write(content)
            sys.stdout.flush()
        return 0
    emit(ctx, cmd, ctx.request(method, path, params=query, body=body, auth=auth))
    return 0


def handle_login(ctx: Context, cmd: Dict[str, Any], args: argparse.Namespace) -> int:
    if getattr(args, "opt_with_token", None):
        key = sys.stdin.readline().strip()
    elif ctx.flag_api_key:
        key = ctx.flag_api_key.strip()
    else:
        if not sys.stdin.isatty():
            raise CLIError("No terminal to prompt on; pipe the key in with 'trendsagi login --with-token'.", EXIT_USAGE)
        print(f"Create an API key at {ctx.spec['api_keys_url']}", file=sys.stderr)
        key = getpass.getpass("Paste your TrendsAGI API key: ").strip()
    if not key:
        raise CLIError("No API key given.", EXIT_USAGE)
    if not key.startswith(API_KEY_PREFIXES):
        raise CLIError("That is not a TrendsAGI API key; keys start with ltc_live_.", EXIT_USAGE)

    profile = ctx.client(api_key=key).request("GET", "/api/user/profile")
    config = dict(ctx.config)
    config["api_key"] = key
    if ctx.base_url != DEFAULT_BASE_URL:
        config["base_url"] = ctx.base_url
    path = write_config(config)
    email = profile.get("email") if isinstance(profile, dict) else None
    print(f"Logged in as {email or 'your account'}. Key saved to {path}", file=sys.stderr)
    env_key = os.environ.get("TRENDSAGI_API_KEY")
    if env_key and env_key != key:
        print("Note: TRENDSAGI_API_KEY is set and takes precedence over the saved key.", file=sys.stderr)
    return 0


def handle_logout(ctx: Context, cmd: Dict[str, Any], args: argparse.Namespace) -> int:
    config = dict(ctx.config)
    if not config.pop("api_key", None):
        print("Not logged in.", file=sys.stderr)
        return 0
    path = write_config(config)
    print(f"Removed the saved key from {path}. To revoke the key itself, delete it at {ctx.spec['api_keys_url']}", file=sys.stderr)
    return 0


def _plan_name(profile: Dict[str, Any]) -> Optional[str]:
    subscription = profile.get("subscription") or {}
    if isinstance(subscription, dict):
        for key in ("plan_name", "name", "plan"):
            if isinstance(subscription.get(key), str):
                return subscription[key]
    return profile.get("stream_type")


def handle_whoami(ctx: Context, cmd: Dict[str, Any], args: argparse.Namespace) -> int:
    from . import exceptions

    client = ctx.client()
    profile = client.request("GET", "/api/user/profile")
    organization = profile.get("organization")
    info: Dict[str, Any] = {
        "email": profile.get("email"),
        "name": profile.get("display_name"),
        "plan": _plan_name(profile),
        "organization": organization.get("name") if isinstance(organization, dict) else None,
        "key_source": ctx.key_source,
        "api": ctx.base_url,
    }
    try:
        usage = client.request("GET", "/api/user/api-usage")
        summary = usage.get("summary") if isinstance(usage, dict) else None
        if isinstance(summary, dict):
            info["requests_today"] = summary.get("requests_today")
            info["daily_limit"] = summary.get("plan_daily_limit")
    except exceptions.APIError:
        pass
    if ctx.json or not ctx.tty:
        print_json(info)
    else:
        print(render_object(info))
    return 0


def handle_insights_generate(ctx: Context, cmd: Dict[str, Any], args: argparse.Namespace) -> int:
    method, path, query, body = build_request(cmd, args)
    queued = ctx.request(method, path, params=query, body=body)
    if not getattr(args, "opt_wait", None):
        emit(ctx, cmd, queued)
        return 0
    trend_id = args.arg_trend_id
    task_id = queued.get("task_id") if isinstance(queued, dict) else None
    status = str((queued or {}).get("status", "")).upper() if isinstance(queued, dict) else ""
    deadline = time.monotonic() + (args.opt_timeout or 180)
    while task_id and status not in _TASK_DONE | _TASK_FAILED:
        if time.monotonic() > deadline:
            raise CLIError(f"Still running after {args.opt_timeout}s; check with 'trendsagi insights status {task_id}'.")
        time.sleep(2)
        result = ctx.request("GET", f"/api/trends/ai-insights/status/{quote(str(task_id), safe='')}")
        status = str(result.get("status", "")).upper()
        if status in _TASK_FAILED:
            raise CLIError(f"Insight generation failed: {result.get('error') or status}")
    print_json(ctx.request("GET", f"/api/trends/{trend_id}/ai-insights"))
    return 0


def handle_sql(ctx: Context, cmd: Dict[str, Any], args: argparse.Namespace) -> int:
    from . import exceptions

    method, path, query, body = build_request(cmd, args)
    if not (body or {}).get("query"):
        raise CLIError("Give a SELECT to run.", EXIT_USAGE)
    try:
        result = ctx.request(method, path, params=query, body=body)
    except exceptions.APIError as exc:
        detail = exc.body if isinstance(exc.body, dict) else {}
        if detail.get("error"):
            lines = [f"Query refused ({detail['error']}): {detail.get('detail') or exc.error_detail}"]
            if detail.get("hint"):
                lines.append(f"Hint: {detail['hint']}")
            if detail.get("position"):
                lines.append(f"At character {detail['position']}.")
            raise CLIError("\n".join(lines))
        raise
    if ctx.json or not ctx.tty:
        print_json(result)
        return 0
    names = [c.get("name") for c in result.get("columns", [])]
    rows = [dict(zip(names, row)) for row in result.get("rows", [])]
    print(render_table(rows, names))
    footer = f"{result.get('row_count', len(rows))} rows in {result.get('elapsed_ms', '?')} ms"
    if result.get("truncated"):
        footer += f" (truncated: {result.get('truncated_reason') or 'limit reached'})"
    print(footer, file=sys.stderr)
    return 0


def handle_tools_call(ctx: Context, cmd: Dict[str, Any], args: argparse.Namespace) -> int:
    arguments = args.opt_args if args.opt_args is not None else {}
    if not isinstance(arguments, dict):
        raise CLIError("--args must be a JSON object.", EXIT_USAGE)
    for key, raw in args.opt_arg or []:
        arguments[key] = _json_value(raw)
    name = quote(args.arg_name, safe="")
    result = ctx.request("POST", f"/api/agent/tools/{name}", body=arguments)
    result = result if isinstance(result, dict) else {}
    texts = [c.get("text", "") for c in result.get("content", []) if isinstance(c, dict)]
    output: Any = "\n".join(texts)
    try:
        output = json.loads(output)
    except ValueError:
        pass
    if result.get("isError"):
        print(output if isinstance(output, str) else json.dumps(output, indent=2), file=sys.stderr)
        return EXIT_ERROR
    if isinstance(output, str):
        print(output)
    else:
        print_json(output)
    return 0


def handle_api(ctx: Context, cmd: Dict[str, Any], args: argparse.Namespace) -> int:
    path = args.arg_path if args.arg_path.startswith("/") else "/" + args.arg_path
    query = {k: v for k, v in (args.opt_query or [])}
    body = args.opt_data
    if args.opt_field:
        if body is None:
            body = {}
        if not isinstance(body, dict):
            raise CLIError("--field needs --data to be a JSON object.", EXIT_USAGE)
        for key, raw in args.opt_field:
            _put(body, key, _json_value(raw))
    method = (args.opt_method or ("POST" if body is not None else "GET")).upper()
    auth = not args.opt_no_auth
    content = ctx.request(method, path, params=query, body=body, auth=auth, raw=True)
    if not content:
        return 0
    try:
        print_json(json.loads(content))
    except ValueError:
        sys.stdout.buffer.write(content)
        sys.stdout.flush()
    return 0


def handle_stream(ctx: Context, cmd: Dict[str, Any], args: argparse.Namespace) -> int:
    import asyncio

    if not ctx.api_key:
        ctx.client()  # raises the not-logged-in error
    ws_base = "ws" + ctx.base_url[len("http"):] if ctx.base_url.startswith("http") else ctx.base_url
    if args.opt_category:
        url = f"{ws_base}/ws/category/{quote(args.opt_category, safe='')}"
    else:
        url = f"{ws_base}/ws/trends"
        if args.opt_follow:
            url += "?follow=" + quote(",".join(args.opt_follow), safe=",")

    async def run() -> None:
        import websockets

        headers = {
            "X-API-Key": ctx.api_key,
            "User-Agent": f"trendsagi-cli/{_version()} python/{platform.python_version()}",
        }
        # websockets 14 renamed extra_headers when its new client became the default.
        major = int(websockets.__version__.split(".")[0])
        header_arg = "additional_headers" if major >= 14 else "extra_headers"
        async with websockets.connect(url, **{header_arg: headers}) as socket:
            print(f"Connected to {url}; press Ctrl-C to stop.", file=sys.stderr)
            async for message in socket:
                if isinstance(message, bytes):
                    message = message.decode("utf-8", "replace")
                try:
                    message = json.dumps(json.loads(message), ensure_ascii=False)
                except ValueError:
                    pass
                print(message, flush=True)

    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        pass
    except OSError as exc:
        raise CLIError(f"Could not connect to {url}: {exc}")
    except Exception as exc:  # websockets raises its own exception types
        raise CLIError(f"Stream ended: {exc}")
    return 0


HANDLERS = {
    "login": handle_login,
    "logout": handle_logout,
    "whoami": handle_whoami,
    "insights_generate": handle_insights_generate,
    "sql": handle_sql,
    "tools_call": handle_tools_call,
    "api": handle_api,
    "stream": handle_stream,
}


# --- legacy subcommands ----------------------------------------------------------


def _copy_file(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(src, dst)


def _copy_tree(src: Path, dst: Path) -> None:
    dst.mkdir(parents=True, exist_ok=True)
    for entry in src.iterdir():
        if entry.name.startswith("__"):
            continue
        if entry.suffix in {".py", ".pyc"}:
            continue
        target = dst / entry.name
        if entry.is_dir():
            _copy_tree(entry, target)
        else:
            _copy_file(entry, target)


def scaffold(template_type: str, output_dir: str = ".") -> None:
    out_dir = Path(output_dir).resolve()
    template_root = Path(__file__).resolve().parent / "templates"

    if template_type == "docker":
        source = Path(template_root / "Dockerfile")
        target = out_dir / "Dockerfile"
        _copy_file(source, target)
        print(f"Created {target}")
        return

    if template_type == "terraform":
        source = Path(template_root / "terraform")
        target = out_dir / "terraform"
        _copy_tree(source, target)
        print(f"Created {target}")
        return

    raise ValueError("template type must be one of: docker, terraform")


# --- entry point ---------------------------------------------------------------


def _describe_api_error(exc: Exception) -> Tuple[str, int]:
    from . import exceptions

    if isinstance(exc, exceptions.AuthenticationError):
        return f"Authentication failed: {exc}. Run 'trendsagi login' with a valid key.", EXIT_AUTH
    if isinstance(exc, exceptions.APIError):
        message = f"Error {exc.status_code}: {exc.error_detail}"
        body = exc.body if isinstance(exc.body, dict) else {}
        for key in ("hint", "upgrade_url", "message"):
            if isinstance(body.get(key), str) and body[key] not in message:
                message += f"\n{body[key]}"
        return message, EXIT_ERROR
    return str(exc), EXIT_ERROR


def main(argv: Optional[List[str]] = None) -> int:
    from . import exceptions

    spec = load_spec()
    parser = build_parser(spec)
    args = parser.parse_args(argv)

    if args.command == "scaffold":
        scaffold(args.template_type, args.output_dir)
        return 0

    try:
        ctx = Context(args, spec)
        if args.command == "mcp":
            from .mcp_server import run

            run(api_key=ctx.api_key, base_url=ctx.base_url, allow_writes=args.allow_writes)
            return 0

        cmd = getattr(args, "_command", None)
        if cmd is None:
            group_parser = getattr(args, "_group_parser", None)
            (group_parser or parser).print_help()
            return EXIT_USAGE
        handler = HANDLERS.get(cmd.get("handler", ""), run_spec_command)
        return handler(ctx, cmd, args)
    except CLIError as exc:
        print(str(exc), file=sys.stderr)
        return exc.code
    except exceptions.TrendsAGIError as exc:
        message, code = _describe_api_error(exc)
        print(message, file=sys.stderr)
        return code
    except KeyboardInterrupt:
        return 130
    except BrokenPipeError:
        # Output piped into head and similar; exit quietly.
        try:
            sys.stdout = open(os.devnull, "w")
        except OSError:
            pass
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
