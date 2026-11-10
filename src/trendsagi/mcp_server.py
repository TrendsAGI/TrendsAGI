"""Model Context Protocol server for TrendsAGI.

Exposes :class:`trendsagi.agent_tools.TrendsAGITools` over stdio so any MCP
client (Claude Desktop, Claude Code, Cursor, VS Code, and others) can query
live trend data without custom glue code. It also serves the packaged
TrendsAGI Agent Skill over MCP (SEP-2640), so a client that supports the
``io.modelcontextprotocol/skills`` extension discovers the workflow
automatically.

Run it with::

    pip install "trendsagi[mcp]"
    trendsagi login                                # once; the CLI and MCP share it
    trendsagi mcp                                  # read-only tools, saved login
    trendsagi mcp --allow-writes

No install is needed for the read-only tools: the same server is hosted at
:data:`HOSTED_MCP_URL` with OAuth sign-in, for Grok, ChatGPT, Claude, Cursor
and any other client that supports remote MCP servers.
"""

from __future__ import annotations

import asyncio
import json
import os
import shutil
from typing import Any, Dict, Optional

from .agent_tools import TrendsAGITools
from .client import TrendsAGIClient
from .skill_catalog import SKILLS_EXTENSION, catalog

SERVER_NAME = "trendsagi"

#: The hosted Streamable HTTP endpoint (OAuth 2.1 sign-in, read-only tools).
HOSTED_MCP_URL = "https://api.trendsagi.com/mcp"

#: Sent to clients on initialize; matches the hosted server's instructions.
SERVER_INSTRUCTIONS = (
    "TrendsAGI measures what is trending across social platforms in real time (volume, velocity, "
    "growth) and turns it into evidence-backed recommendations.\n\n"
    "Use it to help paid media and growth teams decide what to target and when: find topics that "
    "are accelerating before auctions get crowded, choose audiences, keywords and creative angles "
    "backed by measured demand, and spot fading trends so spend can move elsewhere.\n\n"
    "Typical flow: list_trends with sort_by=velocity (optionally a category or search phrase) or "
    "search_trend_insights for a theme; then get_trend_analytics to check the trajectory and "
    "get_trend_ai_insights for audience, sentiment and marketing angles; then list_recommendations "
    "for prioritised actions.\n\n"
    "For questions that need filtering, joins or aggregation (comparing categories, matching the "
    "watchlist against trends, hourly series, counts), call read_data_schema once, then execute_sql "
    "with one read-only PostgreSQL SELECT.\n\n"
    "When no tool fits what the user wants, call find_capability with a short description of the "
    "task to learn whether TrendsAGI supports it and where in the app it is done.\n\n"
    "Report numbers as measurements. A recommendation's confidence score measures how complete its "
    "evidence is, not the probability that the action will work, and TrendsAGI does not measure "
    "conversion lift - never present one as a TrendsAGI figure.\n\n"
    "This server also publishes an Agent Skill over MCP (the io.modelcontextprotocol/skills "
    "extension): skill://trendsagi/SKILL.md. Read it with resources/read before a multi-step "
    "paid-media task. It carries the full workflow, answer contract and guardrails; the tool "
    "descriptions remain the authority on arguments and return shapes."
)


#: Appended to the instructions only when the CLI is installed on the same
#: machine. It is the transport-specific steering the hosted server must not
#: send: an agent reached over stdio from our own CLI can also run the CLI.
CLI_INSTRUCTIONS = (
    "\n\nThis stdio server shares the saved login of the TrendsAGI CLI, and that CLI is available in "
    "this terminal. The `trendsagi` command has a filesystem and no MCP row cap, so when a "
    "result is truncated, when a question needs many pages, or when you want to filter before the data "
    "reaches the model, run the CLI instead: `trendsagi sql \"SELECT ...\" --json`, "
    "`trendsagi api <path> --json`, or any command with `--json`, then grep/jq the output. Ask the user "
    "before running a command that changes state; omit --yes so it prompts them."
)

#: Appended to a tool result that is too large to be comfortably re-read, so
#: the agent learns the CLI escape hatch at the moment it needs it.
CLI_RESULT_HINT = (
    "This result was large. The same login runs the trendsagi CLI in this terminal, and its --json "
    "output has no MCP row cap: for example `trendsagi sql \"SELECT ...\" --json` or "
    "`trendsagi api <path> --json`, piped through jq or grep. Use it for pagination and bulk reads."
)

#: Results longer than this get the CLI hint appended as a second content
#: block. The JSON itself is never edited, so clients that parse it still can.
CLI_HINT_THRESHOLD = 8000


def build_server(tools: TrendsAGITools, cli_available: bool = False) -> Any:
    """Create an MCP ``Server`` that serves ``tools`` and the TrendsAGI skill."""
    try:
        import mcp.types as types
        from mcp.server import Server
        from mcp.shared.exceptions import MCPError
    except ImportError as exc:  # pragma: no cover - exercised only without the extra
        raise SystemExit(
            'The MCP server needs the optional dependency: pip install "trendsagi[mcp]" (Python 3.10+)'
        ) from exc

    from . import __version__

    instructions = SERVER_INSTRUCTIONS + (CLI_INSTRUCTIONS if cli_available else "")
    try:
        server = Server(SERVER_NAME, version=__version__, instructions=instructions)
    except TypeError:  # pragma: no cover - mcp releases without instructions support
        server = Server(SERVER_NAME)

    # SEP-2640: advertise the extension before the handshake is serialized.
    extensions = getattr(server, "extensions", None)
    if isinstance(extensions, dict):
        extensions[SKILLS_EXTENSION] = {"directoryRead": True}

    class _ListSkillsParams(types.PaginatedRequestParams):
        pass

    class _SkillUriParams(types.RequestParams):
        uri: str

    async def list_tools(_ctx: Any, _params: Any) -> Any:
        return types.ListToolsResult(
            tools=[
                types.Tool(name=tool.name, description=tool.description, inputSchema=tool.parameters)
                for tool in tools.tools
            ]
        )

    async def call_tool(_ctx: Any, params: Any) -> Any:
        # The SDK client is synchronous; keep the event loop responsive.
        result = await asyncio.to_thread(tools.call, params.name, params.arguments or {})
        text = json.dumps(result, default=str)
        content = [types.TextContent(type="text", text=text)]
        if cli_available and len(text) >= CLI_HINT_THRESHOLD:
            content.append(types.TextContent(type="text", text=CLI_RESULT_HINT))
        return types.CallToolResult(content=content)

    async def list_skills(_ctx: Any, params: Any) -> Dict[str, Any]:
        return catalog().list_result(getattr(params, "cursor", None))

    async def get_skill(_ctx: Any, params: Any) -> Dict[str, Any]:
        try:
            return catalog().get_result(params.uri)
        except KeyError:
            raise MCPError(
                code=types.INVALID_PARAMS,
                message="No skill is served at " + params.uri,
            ) from None

    async def list_resources(_ctx: Any, _params: Any) -> Dict[str, Any]:
        return catalog().resources_result()

    async def read_resource(_ctx: Any, params: Any) -> Dict[str, Any]:
        try:
            return catalog().read_result(params.uri)
        except KeyError:
            raise MCPError(
                code=types.INVALID_PARAMS,
                message="No resource is served at " + params.uri,
            ) from None

    async def read_directory(_ctx: Any, params: Any) -> Dict[str, Any]:
        try:
            return catalog().directory_result(params.uri)
        except KeyError:
            raise MCPError(
                code=types.INVALID_PARAMS,
                message=params.uri + " is not a directory resource",
            ) from None

    # Register every method explicitly: mcp 2.x has no list_tools()/call_tool()
    # decorators on the low-level Server, and the capabilities are derived from
    # these handlers before create_initialization_options() runs.
    server.add_request_handler("tools/list", types.PaginatedRequestParams, list_tools)
    server.add_request_handler("tools/call", types.CallToolRequestParams, call_tool)
    server.add_request_handler("skills/list", _ListSkillsParams, list_skills)
    server.add_request_handler("skills/get", _SkillUriParams, get_skill)
    server.add_request_handler("resources/list", types.PaginatedRequestParams, list_resources)
    server.add_request_handler("resources/read", types.ReadResourceRequestParams, read_resource)
    server.add_request_handler("resources/directory/read", _SkillUriParams, read_directory)

    return server


async def _serve(tools: TrendsAGITools, cli_available: bool = False) -> None:
    from mcp.server.stdio import stdio_server

    server = build_server(tools, cli_available=cli_available)
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


def cli_is_installed() -> bool:
    """Whether the trendsagi command is on PATH beside this server."""
    return shutil.which("trendsagi") is not None


def run(
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    allow_writes: bool = False,
    cli_available: Optional[bool] = None,
) -> None:
    """Start the stdio MCP server. Blocks until the client disconnects."""
    saved: Dict[str, Any] = {}
    if not api_key or not base_url:
        try:
            from .cli import read_config

            saved = read_config()
        except Exception:  # a missing or unreadable config is not fatal here
            saved = {}
    api_key = api_key or os.getenv("TRENDSAGI_API_KEY") or saved.get("api_key")
    if not api_key:
        raise SystemExit("Not signed in. Run 'trendsagi login', or set TRENDSAGI_API_KEY.")
    client = TrendsAGIClient(
        api_key=api_key,
        base_url=base_url or os.getenv("TRENDSAGI_BASE_URL") or saved.get("base_url") or "https://api.trendsagi.com",
        enable_retry_on_rate_limit=True,
    )
    if cli_available is None:
        cli_available = cli_is_installed()
    asyncio.run(_serve(TrendsAGITools(client, allow_writes=allow_writes), cli_available=cli_available))


def main() -> None:
    """Entry point for the ``trendsagi-mcp`` console script."""
    import argparse

    parser = argparse.ArgumentParser(prog="trendsagi-mcp", description="TrendsAGI MCP server (stdio)")
    add_arguments(parser)
    args = parser.parse_args()
    run(api_key=args.api_key, base_url=args.base_url, allow_writes=args.allow_writes)


def add_arguments(parser: Any) -> None:
    parser.add_argument("--api-key", default=None, help="Defaults to $TRENDSAGI_API_KEY.")
    parser.add_argument("--base-url", default=None, help="Defaults to $TRENDSAGI_BASE_URL or https://api.trendsagi.com.")
    parser.add_argument(
        "--allow-writes",
        action="store_true",
        help="Also expose tools that change account state (watchlist, recommendation workflow).",
    )
