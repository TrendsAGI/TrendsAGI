# TrendsAGI

Live trend intelligence for paid media and growth teams, inside Claude, Claude
Code, Grok, Cursor and Snowflake Cortex Code. Ask what is accelerating in your
market, whether a trend is still rising before you move budget, which audiences
and themes sit behind it, and which ad angles to test. Answers come from
TrendsAGI's measured trend data, read from your own TrendsAGI account.

## What it contains

| Component | Path | Purpose |
| --- | --- | --- |
| Hosted MCP server | `.mcp.json` | `https://api.trendsagi.com/mcp` (Streamable HTTP, OAuth 2.1 sign-in) |
| Skill | `skills/trendsagi/SKILL.md` | Paid-media workflows and reporting rules for the tools |
| Manifests | `.claude-plugin/`, `.grok-plugin/`, `.cursor-plugin/`, `.cortex-plugin/` | Claude, Grok Build / Grok Bot, Cursor, Snowflake Cortex Code |

No code runs on your machine. The plugin only points your assistant at the
hosted server and adds a skill that explains when to use each tool.

The hosted server also publishes the same paid-media workflow as an Agent Skill
over MCP (SEP-2640) at `skill://trendsagi/SKILL.md`. An assistant that supports
the `io.modelcontextprotocol/skills` extension discovers it automatically, so a
server-side skill update does not need a plugin release. The bundled
`skills/trendsagi/SKILL.md` remains the fallback for assistants that do not
support the extension.

## Interactive Trend Radar

Ask Claude to "open the TrendsAGI trend radar". The radar is an MCP App: in
Claude on the web and desktop it opens beside the conversation (or inline where
the side panel is not available), and you and Claude work in the same view.

- Live trends with volume, growth and **paid-targeting eligibility**:
  eligible, needs review, or excluded (politics, conflict, tragedy). Excluded
  trends stay available for research and organic content.
- Your connected ad platforms (Google Ads, Meta, TikTok, LinkedIn, Microsoft,
  Snapchat, Pinterest) and whether each needs reconnecting.
- Per trend: the 7-day trajectory, the insight (audience, keywords, angles)
  and an **ad-targeting dry run**: the keywords, interests or facets the trend
  would add to each selected campaign. Nothing is changed; you apply or
  approve targeting in the TrendsAGI app.
- Claude can filter the radar, select a trend and run the dry run in the open
  view, and the view can hand Claude a campaign-brief request.

Other assistants that support MCP Apps show the same view; the rest receive the
same data as text. Opening the radar from Claude's Artifacts page and showing
the full TrendsAGI app inside it need a Verified directory listing; they turn
on without a plugin update once that happens.

## Tools

All read-only: `open_trend_radar`, `list_trends`, `list_trend_categories`,
`search_trend_insights`, `get_trend`, `get_trend_ai_insights`,
`get_trend_dossier`, `list_web_trends`, `get_trend_analytics`,
`list_ad_platforms`, `preview_ad_targeting` (a dry run),
`list_targeting_proposals`, `list_recommendations`, `list_crisis_events`,
`list_watchlist`, `get_api_usage`, `read_data_schema`, `execute_sql` and
`find_capability`.

## Install

- **Claude Code:** `/plugin marketplace add TrendsAGI/TrendsAGI`, then
  `/plugin install trendsagi@trendsagi`, then `/mcp` to sign in. Or add only the
  server: `claude mcp add --transport http trendsagi https://api.trendsagi.com/mcp`.
- **Claude (web, desktop, mobile):** Settings > Connectors > Add custom connector,
  paste `https://api.trendsagi.com/mcp`, then sign in to TrendsAGI.
- **Grok:** add the TrendsAGI plugin, or add the URL as a remote MCP server.
- **Cursor:** add `{ "mcpServers": { "trendsagi": { "url": "https://api.trendsagi.com/mcp" } } }`.
- **Snowflake Cortex Code (CoCo):** `cortex plugin install github:TrendsAGI/TrendsAGI/plugins/trendsagi`,
  then `/mcp` in a session to sign in. Or add only the server:
  `cortex mcp add trendsagi https://api.trendsagi.com/mcp --type http`.
  There is no public Cortex Code MCP directory, so the plugin installs straight
  from this repository.

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
