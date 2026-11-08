"""Model Context Protocol server for TrendsAGI.

Exposes :class:`trendsagi.agent_tools.TrendsAGITools` over stdio so any MCP
client (Claude Desktop, Claude Code, Cursor, VS Code, and others) can query
live trend data without custom glue code. It also serves the packaged
TrendsAGI Agent Skill over MCP (SEP-2640), so a client that supports the
``io.modelcontextprotocol/skills`` extension discovers the workflow
automatically.

Run it with::

    pip install "trendsagi[mcp]"
    TRENDSAGI_API_KEY=... trendsagi mcp            # read-only tools
    TRENDSAGI_API_KEY=... trendsagi mcp --allow-writes

No install is needed for the read-only tools: the same server is hosted at
:data:`HOSTED_MCP_URL` with OAuth sign-in, for Grok, ChatGPT, Claude, Cursor
and any other client that supports remote MCP servers.
"""

from __future__ import annotations

import asyncio
import json
import os
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


def build_server(tools: TrendsAGITools) -> Any:
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

    try:
        server = Server(SERVER_NAME, version=__version__, instructions=SERVER_INSTRUCTIONS)
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
        return types.CallToolResult(
            content=[types.TextContent(type="text", text=json.dumps(result, default=str))]
        )

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


async def _serve(tools: TrendsAGITools) -> None:
    from mcp.server.stdio import stdio_server

    server = build_server(tools)
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


def run(api_key: Optional[str] = None, base_url: Optional[str] = None, allow_writes: bool = False) -> None:
    """Start the stdio MCP server. Blocks until the client disconnects."""
    api_key = api_key or os.getenv("TRENDSAGI_API_KEY")
    if not api_key:
        raise SystemExit("Set TRENDSAGI_API_KEY (or pass --api-key) to start the TrendsAGI MCP server.")
    client = TrendsAGIClient(
        api_key=api_key,
        base_url=base_url or os.getenv("TRENDSAGI_BASE_URL") or "https://api.trendsagi.com",
        enable_retry_on_rate_limit=True,
    )
    asyncio.run(_serve(TrendsAGITools(client, allow_writes=allow_writes)))


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
