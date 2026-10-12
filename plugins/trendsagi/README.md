# TrendsAGI plugin for Grok, Cursor and Claude

Live trend intelligence for paid media and growth teams, inside your AI
assistant. Ask what is accelerating in your market, whether a trend is still
rising before you move budget, which audiences and themes sit behind it, and
which ad angles to test, answered with TrendsAGI measurements.

## What it contains

| Component | Path | Purpose |
| --- | --- | --- |
| Hosted MCP server | `.mcp.json` / `mcp.json` | `https://api.trendsagi.com/mcp` (Streamable HTTP, OAuth 2.1 sign-in) |
| Skill | `skills/trendsagi/SKILL.md` | Paid-media workflows and reporting rules for the tools |
| Manifests | `.grok-plugin/`, `.cursor-plugin/`, `.claude-plugin/` | Grok Build / Grok Bot, Cursor and Claude Code |

No code runs on your machine: the plugin only points your assistant at the hosted
server and adds a skill.

## Tools

All read-only: `list_trends`, `list_trend_categories`, `search_trend_insights`,
`get_trend`, `get_trend_ai_insights`, `get_trend_analytics`,
`list_recommendations`, `list_crisis_events`, `list_watchlist`, `get_api_usage`.

## Install

- **Grok:** add the TrendsAGI plugin, or add `https://api.trendsagi.com/mcp` as a
  remote MCP server, then sign in to TrendsAGI when prompted.
- **Claude Code:** `/plugin marketplace add TrendsAGI/TrendsAGI`, then
  `/plugin install trendsagi@trendsagi` - or just
  `claude mcp add --transport http trendsagi https://api.trendsagi.com/mcp`.
- **Cursor:** add `{ "mcpServers": { "trendsagi": { "url": "https://api.trendsagi.com/mcp" } } }`.
- **ChatGPT and other MCP clients:** add the server URL as a custom connector.

More: <https://trendsagi.com/mcp>

## Access, network and credentials

- **Network:** the assistant calls `https://api.trendsagi.com` only.
- **Credentials:** none are stored in this plugin. On first connect you sign in to
  TrendsAGI and approve the assistant; TrendsAGI issues that connection its own
  API key, shown as "AI connector: <assistant>" under Profile > API Keys. Delete
  it there to disconnect. Clients without OAuth can instead send an existing
  TrendsAGI API key as `Authorization: Bearer <key>`.
- **Scope:** read-only. Calls count toward your plan's API limits.

## License

MIT. See [LICENSE](LICENSE).
