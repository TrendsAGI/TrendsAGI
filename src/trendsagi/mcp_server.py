"""Model Context Protocol server for TrendsAGI.

Exposes :class:`trendsagi.agent_tools.TrendsAGITools` over stdio so any MCP
client (Claude Desktop, Claude Code, Cursor, VS Code, and others) can query
live trend data without custom glue code.

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
from typing import Any, Dict, List, Optional

from .agent_tools import TrendsAGITools
from .client import TrendsAGIClient

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
    "When no tool fits what the user wants, call find_capability with a short description of the "
    "task to learn whether TrendsAGI supports it and where in the app it is done.\n\n"
    "Report numbers as measurements. A recommendation's confidence score measures how complete its "
    "evidence is, not the probability that the action will work, and TrendsAGI does not measure "
    "conversion lift - never present one as a TrendsAGI figure."
)


def build_server(tools: TrendsAGITools) -> Any:
    """Create an MCP ``Server`` that serves ``tools``."""
    try:
        import mcp.types as types
        from mcp.server import Server
    except ImportError as exc:  # pragma: no cover - exercised only without the extra
        raise SystemExit(
            'The MCP server needs the optional dependency: pip install "trendsagi[mcp]" (Python 3.10+)'
        ) from exc

    try:
        server = Server(SERVER_NAME, instructions=SERVER_INSTRUCTIONS)
    except TypeError:  # pragma: no cover - mcp releases without instructions support
        server = Server(SERVER_NAME)

    @server.list_tools()
    async def list_tools() -> List[types.Tool]:
        return [
            types.Tool(name=tool.name, description=tool.description, inputSchema=tool.parameters)
            for tool in tools.tools
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: Optional[Dict[str, Any]]) -> List[types.TextContent]:
        # The SDK client is synchronous; keep the event loop responsive.
        result = await asyncio.to_thread(tools.call, name, arguments or {})
        return [types.TextContent(type="text", text=json.dumps(result, default=str))]

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
