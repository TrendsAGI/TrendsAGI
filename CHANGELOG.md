# Changelog

All notable changes to the official TrendsAGI Python client are documented here.

## [0.20.0] - 2026-11-10

### Added

- **Browser login.** `trendsagi login` now uses the OAuth 2.0 device flow
  (RFC 8628). It prints a short code and URL, opens the browser when there is
  one, and saves the API key the server issues after approval. `--no-browser`
  prints the URL only; `--with-token`, `--api-key` and `TRENDSAGI_API_KEY`
  still work for CI and non-interactive machines. Both the Python and npm CLI
  use the same flow and the same config file.
- **One login for the CLI and the local MCP server.** `trendsagi mcp` starts
  the stdio server with the saved login, and `trendsagi-mcp` now reads the same
  config when no key is in the environment.
- **CLI-aware MCP steering.** When the stdio server is started beside the
  `trendsagi` command, its instructions tell the agent that the CLI exists and
  how to use it for bulk reads and pagination. A tool result over 8,000
  characters gets a second content block pointing at `trendsagi ... --json`.
  The hosted server is unchanged.
- `npx trendsagi mcp` starts `trendsagi-mcp` when it is installed, so the npm
  CLI bridges to the same server instead of only printing an install hint.

### Changed

- The login command's help, the README quickstart and the local MCP setup no
  longer ask for a pasted key by default.

## [0.19.0] - 2026-11-08

### Added

- **Social Evidence.** `get_social_evidence()` reads the stored report for a
  trend (free), `run_social_evidence()` runs or refreshes it (one credit per
  run), and `get_social_evidence_credits()` /
  `create_social_evidence_checkout()` cover the balance and one-time packs.
  `SocialEvidenceReport` and its section, quality and credit models are
  exported from `trendsagi.models`.
- **Deep Dive, dossier and discovery.** `get_trend_dossier()`,
  `get_trend_discoveries()`, `enrich_trend()`, `get_search_demand()`,
  `get_brand_momentum()`, `get_trend_creators()` and `ask_trend()` map the
  on-demand enrichment and grounded-answer endpoints. `get_trends()` accepts
  `include="dossier"` to attach the compact resolved entity to list rows.
- **CLI.** `trends dossier`, `trends discoveries`, `trends enrich`,
  `trends search-demand`, `trends brand-momentum`, `trends creators`,
  `trends ask`, `trends social-evidence get|run`, and
  `credits social-evidence` / `credits buy-social-evidence`.
- **Agent tools.** The local MCP surface adds `get_trend_dossier`,
  `list_web_trends`, `get_search_demand`, `get_brand_momentum`,
  `get_trend_creators`, `ask_trend`, `get_social_evidence` and
  `get_social_evidence_credits`. `enrich_trend`, `run_social_evidence` and
  `create_social_evidence_checkout` are exposed only with
  `--allow-writes` because they reserve credits or start a purchase flow.
- **OpenAPI.** `openapi.json` is regenerated from the current public API
  catalog, including the Social Evidence, Deep Dive, dossier and discovery
  endpoints and without the retired n8n connector.

### Changed

- The hosted MCP server keeps its curated 15-tool read-only surface. The new
  credit-spending tools stay in the local SDK behind `--allow-writes`, and
  free Social Evidence reads stay in the SDK because a report is trend-scoped
  and may have been paid for by another customer.

## [0.18.0] - 2026-11-06

### Added

- **Skills over MCP.** The bundled stdio server declares
  `io.modelcontextprotocol/skills` (SEP-2640) and serves the TrendsAGI
  paid-media skill at `skill://trendsagi/SKILL.md`. `skills/list` and
  `skills/get` return a complete manifest with a SHA-256 digest and byte size
  for every file; `resources/read` serves the files and
  `resources/directory/read` lists subdirectories. The skill covers the tool
  surface, targeting and budget decisions, read-only SQL, the answer contract
  and error handling. Clients that support the extension load it automatically;
  clients that do not still receive the server instructions and tool
  descriptions.

### Changed

- The `mcp` extra now requires `mcp>=2.3,<3`, the first release line with the
  2026-07-28 protocol surface and extension capabilities. Python 3.10+ is still
  required for the local MCP server.
- The package ships `src/trendsagi/skills/trendsagi/` as package data, so the
  served skill and its references are installed with the wheel.

## [0.17.2] - 2026-11-02

### Added

- `TrendsAGITools.webmcp()` descriptors carry a `title`, the short label WebMCP
  browsers show in their tool lists. The titles match the hosted MCP server's.

### Fixed

- [`webmcp/trendsagi-webmcp.js`](webmcp/trendsagi-webmcp.js) returns each tool
  result as an object. The WebMCP draft JSON-serializes whatever `execute`
  resolves to, so the JSON text it returned before reached the agent as one
  escaped string. A cancelled call now also aborts its request.

## [0.17.1] - 2026-10-27

### Added

- [`agent-sdk/`](agent-sdk/): a Cursor Agent SDK project that reaches the hosted MCP
  server through one connection file (`bot/mcp-connections/trendsagi.ts`), with
  instructions, a trend-brief skill, hosting settings and smoke evals. The README has a
  "Build an agent with Cursor Agent SDK" section.

### Fixed

- `GoogleAdsExecutor` now calls Google Ads API v26, the current major. Google
  retires older majors on a rolling schedule (v22 went away in October 2026),
  and a retired major makes every read and mutate fail with a bare "Request
  contains an invalid argument."
- Positive Google Ads keywords are written through `adGroupCriteria:mutate`
  with an `ad_group_id`. Campaign criteria only support negative keywords, so
  sending positive keywords there was rejected by Google. The executor now
  raises a clear `ValueError` when positive keywords are supplied without an
  ad group instead of sending an invalid request.
- Negative keywords still go to `campaignCriteria:mutate` and do not require an
  ad group.

## [0.17.0] - 2026-10-21

### Added

- A command line for the whole API. `trendsagi login` checks an API key and saves it
  to `~/.config/trendsagi/config.json` (owner-only on macOS and Linux; `%APPDATA%` on
  Windows), then one command per action: `trends`, `insights`, `recommendations`,
  `crisis`, `watchlist`, `sql`, `schema`, `tools`, `find`, `usage`, `status`,
  `webhooks`, `exports`, `ads`, `integrations` and `stream`, plus `whoami`, `logout`
  and `api` for any endpoint without its own command. Lists print as tables in a
  terminal and as JSON when piped or with `--json`. Commands that delete something or
  change live ads ask first (`--yes` skips the question). Exit code 4 means a missing
  or rejected key.
- `src/trendsagi/cli_spec.json` declares every command; the Node.js build of the same
  CLI in [`npm/`](npm/) reads the same file, and a test keeps the copies identical.
- `TrendsAGIClient.request(method, path, params=None, json=None, auth=True, raw=False)`
  calls any endpoint, including ones without a dedicated method.

### Changed

- `trendsagi mcp` falls back to the key saved by `trendsagi login`.
- The CLI sends `User-Agent: trendsagi-cli/<version> python/<version>`.
- A successful response with an empty body returns `None` instead of raising.

### Fixed

- The README showed `trendsagi scaffold --output`; the flag is `--output-dir`.

## [0.16.0] - 2026-10-21

### Added

- `TrendsAGITools.webmcp()`: the tools as WebMCP descriptors (`name`, `description`,
  `inputSchema`, `annotations`) for a web page to register with
  `document.modelContext.registerTool()`, while your server runs each call with
  `tools.call()` and keeps the API key. `readOnlyHint` is false only for the opt-in
  write tools; tools whose results quote social posts or generated insights carry
  `untrustedContentHint`.
- `AgentTool.untrusted_output` marks those tools in the registry.
- [`webmcp/`](webmcp/) in the repository: a dependency-free browser module and a
  FastAPI example that put TrendsAGI tools on your own site.

### Notes

- The TrendsAGI app (app.trendsagi.com) now registers the same read-only tools with
  WebMCP for signed-in users, and the API serves them at `GET /api/agent/tools` and
  `POST /api/agent/tools/{name}`. See <https://trendsagi.com/webmcp>.

## [0.15.0] - 2026-10-20

### Added

- `execute_sql` and `read_data_schema` agent tools (read-only), and
  `TrendsAGIClient.execute_sql(query, max_rows=None, max_result_bytes=None)` /
  `TrendsAGIClient.get_data_schema()`: run one read-only PostgreSQL SELECT over
  trends, trend readings, AI insights, the watchlist, recommendations and crisis
  events, for questions that need filters, joins or aggregation. Available in every
  tool format and in `trendsagi mcp`; the hosted MCP server has them too.
- `exceptions.QueryError` (a subclass of `APIError`) with `code`, `hint` and
  `position` for refused or failed queries. Agent tools return these fields to the
  model so it can fix its SQL.
- `APIError.body` holds the decoded JSON error response.

### Changed

- The local MCP server's instructions point assistants at SQL for questions that
  need filtering, joins or aggregation, matching the hosted server.

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
