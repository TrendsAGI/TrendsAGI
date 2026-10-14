# Changelog

All notable changes to the official TrendsAGI Python client are documented here.

## [0.14.0] - 2026-10-14

### Added

- `find_capability` agent tool (read-only) and `TrendsAGIClient.find_capability(goal)`:
  ask whether TrendsAGI can do a task and get the covering tools or the app page,
  best match first. Available in every tool format and in `trendsagi mcp`; the
  hosted MCP server has it too.
- Requests now send a `User-Agent: trendsagi-python/<version>` header.

### Changed

- The local MCP server's instructions tell assistants to use `find_capability`
  when no other tool fits, matching the hosted server.

## [0.13.0] - 2026-10-12

### Added

- Hosted MCP server at `https://api.trendsagi.com/mcp` (Streamable HTTP, OAuth 2.1
  sign-in, read-only tools), exposed as `trendsagi.mcp_server.HOSTED_MCP_URL`.
- `plugins/trendsagi`: a Grok Build / Grok Bot, Cursor and Claude Code plugin that
  bundles the hosted server and a paid-media skill, plus self-hosted marketplace
  catalogs at the repository root (`/plugin marketplace add TrendsAGI/TrendsAGI`).
- The local MCP server sends the same server instructions as the hosted one.

### Changed

- Tool descriptions now say how each result informs targeting, timing and creative
  decisions, so assistants reach for the right tool in paid-media conversations.

## [0.12.0] - 2026-10-11

### Added

- `TrendsAGITools`: twelve agent tools with one JSON-schema contract exported for
  OpenAI Chat Completions, the OpenAI Responses API, Anthropic tool use, and
  LangChain. Read-only by default; write tools need `allow_writes=True`.
  `call()` returns `{"error": ...}` instead of raising so agent loops can recover.
- MCP server: `trendsagi mcp` / `trendsagi-mcp` (install `trendsagi[mcp]`,
  Python 3.10+) for Claude Desktop, Claude Code, Cursor, VS Code and other MCP clients.
- `get_trends(category=..., search=...)` filters, which the API already supported.

## [0.11.0] - 2026-10-02

- Removes the Sovereign AI resilience beta methods, evidence export, source status,
  location preferences, and their documentation after the product rollback.
- Keeps the earlier crisis-event list/action methods and the paid-media
  recommendation decision briefs introduced before version 0.10.0.
- Restores a trend-discovery example that previews advertising changes by default.
- Existing 0.10.0 installations should upgrade before using the current API;
  the removed resilience beta methods no longer have backend routes.

## [0.9.0] - Included in 0.11.0

### Added

- Typed recommendation decision briefs with supporting evidence, evidence-completeness
  confidence, expected benefit, urgency, data quality, and next steps.
- Explicit recommendation ordering with `priority` (default) and `newest` modes.

### Changed

- Recommendation requests now default to 10 new items in priority order and cap page
  size at the API maximum of 100.
- Recommendation type, source-trend, priority, status, interest-match, and ordering
  filters are validated and serialized consistently with the API contract.
- Recommendation actions now validate IDs, workflow states, exclusive payload fields,
  and the 500-character feedback limit before making a network request.
- `source_trend_id` accepts both string and integer values for compatibility across API
  record generations.

### Compatibility

- `decision_brief` is optional, so responses from older TrendsAGI API deployments remain
  valid in SDK 0.9.0.
