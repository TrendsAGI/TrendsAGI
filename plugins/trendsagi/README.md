# TrendsAGI

Live trend intelligence for paid media and growth teams, inside Claude, Claude
Code, Grok and Cursor. Ask what is accelerating in your market, whether a trend
is still rising before you move budget, which audiences and themes sit behind
it, and which ad angles to test. Answers come from TrendsAGI's measured trend
data, read from your own TrendsAGI account.

## What it contains

| Component | Path | Purpose |
| --- | --- | --- |
| Hosted MCP server | `.mcp.json` | `https://api.trendsagi.com/mcp` (Streamable HTTP, OAuth 2.1 sign-in) |
| Skill | `skills/trendsagi/SKILL.md` | Paid-media workflows and reporting rules for the tools |
| Manifests | `.claude-plugin/`, `.grok-plugin/`, `.cursor-plugin/` (with `mcp.json`) | Claude, Grok Build / Grok Bot, Cursor |

No code runs on your machine. The plugin only points your assistant at the
hosted server and adds a skill that explains when to use each tool.

## Tools

All read-only: `list_trends`, `list_trend_categories`, `search_trend_insights`,
`get_trend`, `get_trend_ai_insights`, `get_trend_analytics`,
`list_recommendations`, `list_crisis_events`, `list_watchlist`, `get_api_usage`.

## Install

- **Claude Code:** `/plugin marketplace add TrendsAGI/TrendsAGI`, then
  `/plugin install trendsagi@trendsagi`, then `/mcp` to sign in. Or add only the
  server: `claude mcp add --transport http trendsagi https://api.trendsagi.com/mcp`.
- **Claude (web, desktop, mobile):** Settings > Connectors > Add custom connector,
  paste `https://api.trendsagi.com/mcp`, then sign in to TrendsAGI.
- **Grok:** add the TrendsAGI plugin, or add the URL as a remote MCP server.
- **Cursor:** add `{ "mcpServers": { "trendsagi": { "url": "https://api.trendsagi.com/mcp" } } }`.

Setup guide, plans and example prompts: <https://trendsagi.com/mcp>

## Requirements

A TrendsAGI account. Any plan can read trends, trajectories, insights,
recommendations and the watchlist. Insight search needs the Advantage plan or
higher, and crisis events need Scale or higher. Each tool call counts as one
request toward the plan's daily API limit, and each connection uses one of the
plan's API keys.

## Data, network and credentials

- **Network:** the assistant calls `https://api.trendsagi.com` only. The plugin
  sends nothing anywhere else and runs no local code.
- **Credentials:** none are stored in this plugin. On first use you sign in to
  TrendsAGI and approve the assistant on a consent page that names it and shows
  where access is sent. TrendsAGI then issues that connection its own API key,
  listed as "AI connector: <assistant>" under Profile > API Keys; delete it to
  disconnect.
- **What TrendsAGI receives:** only the tool requests the assistant sends, such
  as a category, a search phrase or a trend id, never your conversation. Those
  requests are logged like any other API call.
- **Scope:** read-only. The connection cannot change your account, create or
  edit campaigns, or spend money.

## Privacy

TrendsAGI's privacy policy, including how AI assistant connections are handled
and how long their keys are kept: <https://trendsagi.com/privacy>

## Support

<https://trendsagi.com/contact> or contact@trendsagi.com

## License

MIT. See [LICENSE](LICENSE).
