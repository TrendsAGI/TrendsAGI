# TrendsAGI

[![PyPI Version](https://img.shields.io/pypi/v/trendsagi.svg)](https://pypi.org/project/trendsagi/)
[![npm Version](https://img.shields.io/npm/v/trendsagi.svg)](https://www.npmjs.com/package/trendsagi)
[![Python Versions](https://img.shields.io/pypi/pyversions/trendsagi.svg)](https://pypi.org/project/trendsagi/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Real-time trend intelligence for your code and your AI agents: what is trending on social platforms right now, with measured volume, velocity and growth, AI insights on why each topic is moving, evidence-backed recommendations, crisis alerts and watchlists. Paid media and growth teams use it to target what is rising, time spend to the trend curve and brief creative on measured demand.

| | |
| --- | --- |
| **Python client** | `TrendsAGIClient`, a typed REST client |
| **Command line** | `trendsagi`, one command per API action, tables in a terminal and JSON in a pipe |
| **Agent tools** | `TrendsAGITools` for OpenAI, Claude, LangChain and WebMCP |
| **Hosted MCP server** | `https://api.trendsagi.com/mcp` for Claude, ChatGPT, Grok, Cursor and Gemini CLI |
| **Browser agents (WebMCP)** | Signed in to app.trendsagi.com, your browser's agent gets the same tools ([`webmcp/`](webmcp/)) |
| **Local MCP server** | `trendsagi mcp`, the same tools over stdio |
| **Plugins** | Claude, Grok and Cursor plugin in [`plugins/trendsagi`](plugins/trendsagi), Gemini CLI extension at the repo root |
| **Ad execution** | Executors that preview, then apply, Google, Meta, TikTok and LinkedIn ad changes from your own infrastructure |

## Install

```bash
pip install trendsagi            # client, agent tools and the trendsagi command
pip install "trendsagi[mcp]"     # adds the local MCP server (Python 3.10+)
pipx install trendsagi           # just the command line, in its own environment
npx trendsagi --help             # or the same command line from npm (Node.js 18+)
```

Create an API key under Profile > API Keys at [app.trendsagi.com](https://app.trendsagi.com) and export it:

```bash
export TRENDSAGI_API_KEY="your_api_key"
```

## Quickstart

```python
import os
from trendsagi import TrendsAGIClient

client = TrendsAGIClient(api_key=os.environ["TRENDSAGI_API_KEY"])

# Fastest-moving Technology topics right now
trends = client.get_trends(category="Technology", sort_by="velocity", limit=5)
for trend in trends.trends:
    print(trend.id, trend.name, trend.volume)

# Why is the top one moving?
insight = client.get_ai_insights(trends.trends[0].id)
if insight:
    print(insight.sentiment_summary, insight.key_themes)
```

## Command line

```bash
trendsagi login                  # paste an API key; saved to ~/.config/trendsagi/config.json
trendsagi trends list --category Technology --sort velocity --limit 10
trendsagi insights get 123       # audience, sentiment and marketing angles
trendsagi sql "SELECT category, count(*) FROM trends GROUP BY 1 ORDER BY 2 DESC"
trendsagi recommendations list --priority high
trendsagi watchlist add "oat milk" --threshold 50000 --email
trendsagi api /api/integrations/delivery/health -q lookback_hours=24   # any endpoint
```

| Commands | What they do |
| --- | --- |
| `login`, `logout`, `whoami` | Save, forget and check the API key |
| `trends` `list` `get` `analytics` `categories` `autocomplete` | Trending topics with measured volume, velocity and growth |
| `insights` `get` `generate [--wait]` `status` `search` | AI insights per trend |
| `recommendations` `list` `action` `feedback` | Evidence-backed recommendations and their workflow status |
| `crisis` `list` `action` | Crisis events: acknowledge, archive, reopen |
| `watchlist` `list` `add` `remove` | Tracked keywords and categories, with alerts |
| `sql`, `schema` | One read-only PostgreSQL SELECT over your data, and the tables it can read |
| `tools` `list` `call`, `find` | The agent tools, and whether TrendsAGI can do a task |
| `webhooks`, `exports` | Create, change, test and run webhooks and data exports |
| `ads` `providers` `resources` `preview` `apply` `report` `report-export` | Connected ad platforms: trend-based changes and reports |
| `integrations` `availability` `status` `health` `value` | Integration status and delivery health |
| `stream` | Live trend updates as JSON lines |
| `usage`, `status`, `api` | API usage, service status, and any endpoint without its own command |

Every command has `--help`. In a terminal, lists print as tables; piped or with `--json` they print JSON, so `trendsagi trends list | jq` works. The key comes from `--api-key`, then `TRENDSAGI_API_KEY`, then the saved login. Commands that delete something or change live ads ask first; pass `--yes` in scripts. Exit codes: 0 success, 1 API error, 2 invalid usage, 4 missing or rejected key.

The commands are declared once in [`src/trendsagi/cli_spec.json`](src/trendsagi/cli_spec.json); a dependency-free Node.js build of the same CLI lives in [`npm/`](npm/) and is published as [`trendsagi` on npm](https://www.npmjs.com/package/trendsagi). Guide: [trendsagi.com/api-docs/integrations/cli](https://trendsagi.com/api-docs/integrations/cli).

The client calls any endpoint too: `client.request("GET", "/api/integrations/delivery/health", params={"lookback_hours": 24})`.

## Use TrendsAGI in your AI assistant (no install)

Add the hosted MCP server, sign in to TrendsAGI and approve the connection:

| Assistant | Setup |
| --- | --- |
| Claude | Open [TrendsAGI in the Claude directory](https://claude.ai/directory/trendsagi), or Settings > Connectors > Add custom connector with the URL below |
| Claude Code | `claude mcp add --transport http trendsagi https://api.trendsagi.com/mcp`, or `/plugin marketplace add TrendsAGI/TrendsAGI` then `/plugin install trendsagi@trendsagi` |
| ChatGPT | Add a custom connector with the URL below |
| Grok | Install the TrendsAGI plugin, or add the URL as a remote MCP server |
| Cursor | `{ "mcpServers": { "trendsagi": { "url": "https://api.trendsagi.com/mcp" } } }` |
| Gemini CLI | `gemini extensions install https://github.com/TrendsAGI/TrendsAGI` |

```text
https://api.trendsagi.com/mcp
```

Then ask *"What is accelerating fastest in Technology this week, and who should I target with it?"* The hosted tools are read-only, and each call counts as one API request. Each connection gets its own key, listed as "AI connector: <assistant>" under Profile > API Keys; delete it to disconnect. Clients without OAuth can send an API key as `Authorization: Bearer <key>`. Guide: [trendsagi.com/mcp](https://trendsagi.com/mcp).

## Use TrendsAGI from your browser's agent (WebMCP)

[WebMCP](https://webmachinelearning.github.io/webmcp/) lets a web page hand tools to the AI agent built into the browser (Chrome and Edge in origin trials, ChatGPT desktop, Brave Leo). While you are signed in to [app.trendsagi.com](https://app.trendsagi.com), the app registers TrendsAGI's read-only tools with `document.modelContext`, so the agent uses them with your session: no connector or API key, and calls count as app use rather than API usage. trendsagi.com offers public tools (docs search, trend reports, plans and the free calculators) to every visitor.

To put TrendsAGI tools on **your own** site, register them in your page and run them on your server, which keeps the API key:

```python
tools = TrendsAGITools(TrendsAGIClient(api_key=os.environ["TRENDSAGI_API_KEY"]))

tools.webmcp()                     # serve to your page: name, description, inputSchema, annotations
tools.call("list_trends", args)    # run the call your page forwards
```

[`webmcp/`](webmcp/) has the browser module and a FastAPI server. Guide: [trendsagi.com/webmcp](https://trendsagi.com/webmcp).

## Agent tools

One registry, every format. The tools are **read-only by default**; `add_to_watchlist` and `update_recommendation` appear only with `allow_writes=True` (or `trendsagi mcp --allow-writes`).

| Tool | What the agent gets |
| --- | --- |
| `list_trends` | Trending topics by category or phrase, sorted by velocity, growth or volume |
| `list_trend_categories` | Valid category names |
| `search_trend_insights` | Trends and insights matching a theme |
| `get_trend` / `get_trend_analytics` | One trend and its volume time series |
| `get_trend_ai_insights` | Summary, key themes, sentiment, audience, marketing angles |
| `list_recommendations` | Evidence-backed actions with a decision brief |
| `list_crisis_events` | Reputation and crisis events for monitored topics |
| `list_watchlist` / `get_api_usage` | Watched topics and remaining daily quota |
| `read_data_schema` / `execute_sql` | Read-only SQL for questions that need filters, joins or aggregation |
| `find_capability` | Whether TrendsAGI can do a task, and which tool or app page does it |

### OpenAI

```python
import json, os
from openai import OpenAI
from trendsagi import TrendsAGIClient, TrendsAGITools

tools = TrendsAGITools(TrendsAGIClient(api_key=os.environ["TRENDSAGI_API_KEY"]))
openai = OpenAI()
messages = [{"role": "user", "content": "Find a fast-rising Technology trend and suggest a campaign angle."}]

while True:
    reply = openai.chat.completions.create(model="gpt-5-mini", messages=messages, tools=tools.openai())
    message = reply.choices[0].message
    messages.append(message)
    if not message.tool_calls:
        print(message.content)
        break
    for call in message.tool_calls:
        result = tools.call(call.function.name, call.function.arguments)
        messages.append({"role": "tool", "tool_call_id": call.id, "content": json.dumps(result)})
```

### Claude, LangChain and others

```python
tools.anthropic()         # Anthropic Messages API tools=
tools.openai_responses()  # OpenAI Responses API tools=
tools.langchain()         # LangChain StructuredTools (pip install "trendsagi[langchain]")
tools.webmcp()            # WebMCP descriptors for document.modelContext.registerTool
```

With Claude, pass `tools=tools.anthropic()` and answer each `tool_use` block with `{"type": "tool_result", "tool_use_id": block.id, "content": json.dumps(tools.call(block.name, block.input))}`. `tools.call` never raises: errors come back as `{"error": ...}` so the model can read a rate limit or a bad argument and recover.

### Local MCP server

```bash
pip install "trendsagi[mcp]"
claude mcp add trendsagi --env TRENDSAGI_API_KEY=your_api_key -- trendsagi mcp
```

Or in any MCP client's JSON config (Claude Desktop, Cursor, VS Code):

```json
{ "mcpServers": { "trendsagi": { "command": "trendsagi-mcp", "env": { "TRENDSAGI_API_KEY": "your_api_key" } } } }
```

## Query with SQL

For answers no single endpoint returns, such as growth by category or the trends that match a watchlist:

```python
schema = client.get_data_schema()   # tables, columns, rules, examples
result = client.execute_sql(
    """
    SELECT category, count(*) AS trends, round(avg(growth_pct)::numeric, 1) AS avg_growth_pct
    FROM trends
    WHERE last_seen_at > now() - interval '7 days' AND growth_pct IS NOT NULL
    GROUP BY category ORDER BY avg_growth_pct DESC
    """,
    max_rows=20,
)
print(result["columns"], result["rows"])
```

Tables: `trends`, `trend_snapshots` (90 days of readings), `trend_categories`, `trend_insights`, `watchlist`, `recommendations` and `crisis_events`; the last three only contain your own account's rows. Queries are one validated `SELECT`, run read-only for at most 5 seconds, and count as one API request. A refused query raises `exceptions.QueryError` with a `code` (such as `unknown_table` or `timeout`), plus `hint` and `position` when known.

## Recommendations with decision briefs

```python
recommendations = client.get_recommendations(match_user_interests=True, priority="high", sort="priority", limit=10)
for rec in recommendations.recommendations:
    brief = rec.decision_brief
    if brief and brief.actionable:
        print(rec.title, brief.why_now, brief.next_steps[:1])
```

Each brief explains why an action is timely, the measured signals behind it and concrete next steps. Its confidence score measures evidence completeness, not the chance of success; use `actionable` and `data_quality` to hold back when signals are stale or incomplete.

## Ad execution in your own infrastructure

`GoogleAdsExecutor`, `MetaAdsExecutor`, `TikTokAdsExecutor` and `LinkedInAdsExecutor` take credentials at runtime, use deterministic idempotency keys, and support dry-run previews and strict validation:

```python
from trendsagi.integrations import GoogleAdsExecutor

insight = client.get_ai_insights(trend_id)  # the trend you decided to act on
google = GoogleAdsExecutor({
    "access_token": os.environ["GOOGLE_ADS_ACCESS_TOKEN"],
    "developer_token": os.environ["GOOGLE_ADS_DEVELOPER_TOKEN"],
})
# Positive keywords target an ad group; campaign criteria can only exclude.
preview = google.apply_targeting(
    insight,
    customer_id="1234567890",
    campaign_id="9876543210",
    ad_group_id="1122334455",
    dry_run=True,
    strict_mode=True,
)
print(preview.response)  # inspect before any real change
```

See [`INTEGRATIONS_BYOC.md`](INTEGRATIONS_BYOC.md) for every executor.

## Errors

```python
from trendsagi import exceptions

try:
    client.get_trends(limit=5)
except exceptions.RateLimitError:
    ...  # back off and retry
except exceptions.AuthenticationError:
    ...  # invalid or revoked key
```

## Other commands

```bash
trendsagi mcp [--allow-writes]                              # MCP server over stdio
trendsagi scaffold --type docker --output-dir ./runner      # executor runner template
trendsagi scaffold --type terraform --output-dir ./infra    # infrastructure template
```

## Plans and limits

The free Developer plan includes one API key and 100 API calls a day; Advantage, Scale and Enterprise raise the daily limit and add keys and team features. Calls above the daily allowance are billed as overage. See [pricing](https://trendsagi.com/subscription).

## Links

- [API documentation](https://trendsagi.com/api-docs) and [endpoint reference](https://trendsagi.com/api-docs/reference)
- [CLI guide](https://trendsagi.com/api-docs/integrations/cli)
- [MCP server guide](https://trendsagi.com/mcp) and [WebMCP guide](https://trendsagi.com/webmcp)
- [Changelog](CHANGELOG.md)
- Support: [trendsagi.com/contact](https://trendsagi.com/contact) or contact@trendsagi.com

## License

MIT. See [LICENSE](LICENSE).
