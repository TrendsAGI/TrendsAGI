# TrendsAGI Official Python Client

[![PyPI Version](https://img.shields.io/pypi/v/trendsagi.svg)](https://pypi.org/project/trendsagi/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python Versions](https://img.shields.io/pypi/pyversions/trendsagi.svg)](https://pypi.org/project/trendsagi/)

## About
Real-time trend intelligence for your code and your AI agents.

`trendsagi` gives Python apps and autonomous agents structured access to what is trending right now on social platforms: measured volume and growth, AI insights explaining why a topic is moving, evidence-backed recommendations, crisis alerts, and watchlists. Paid media and growth teams use it to target what is rising, time spend to the trend curve, and brief creative on measured demand. It ships with:

- A typed REST client (`TrendsAGIClient`).
- **Agent tools** (`TrendsAGITools`) for OpenAI function calling, Anthropic tool use, and LangChain.
- An **MCP server** (`trendsagi mcp`) for Claude Desktop, Claude Code, Cursor, VS Code, and any other Model Context Protocol client.
- A **plugin for Grok, Cursor and Claude** ([`plugins/trendsagi`](./plugins/trendsagi)) backed by the hosted MCP server.
- BYOC executors that preview or apply Google/Meta/TikTok/LinkedIn ad changes from your own infrastructure.

## Use TrendsAGI in Grok, ChatGPT, Claude or Cursor (no install)

TrendsAGI runs a hosted MCP server with OAuth sign-in:

```text
https://api.trendsagi.com/mcp
```

Add that URL as a remote MCP server, custom connector or plugin in your assistant, sign in to TrendsAGI, and approve the connection. Then ask things like *"What is accelerating fastest in Technology this week, and who should I target with it?"* or *"Is this trend still rising, or should I pull spend?"*

- **Grok:** install the TrendsAGI plugin, or add the URL as a remote MCP server.
- **Claude Code:** `claude mcp add --transport http trendsagi https://api.trendsagi.com/mcp`, or `/plugin marketplace add TrendsAGI/TrendsAGI` then `/plugin install trendsagi@trendsagi`.
- **Cursor:** `{ "mcpServers": { "trendsagi": { "url": "https://api.trendsagi.com/mcp" } } }`.
- **ChatGPT and others:** add the URL as a custom connector.

The hosted tools are read-only and count toward your plan's API limits. Each connection gets its own key, listed as "AI connector: <assistant>" under Profile > API Keys; delete it to disconnect. Clients without OAuth can send an existing API key as `Authorization: Bearer <key>`. Setup guide: [trendsagi.com/mcp](https://trendsagi.com/mcp).

## Plan Notes (API Access)
- Developer plan includes:
  - 1 API integration connection
  - 100 API calls/day included
  - Overage billing above included daily usage
- Advantage/Scale unlock higher daily API limits, more keys, and expanded team workflows.

## Resources
- Website: [https://trendsagi.com](https://trendsagi.com)
- API Docs: [https://trendsagi.com/api-docs](https://trendsagi.com/api-docs)
- Endpoint Reference: [https://trendsagi.com/api-docs#endpoints](https://trendsagi.com/api-docs#endpoints)
- BYOC Integrations Guide (repo): [`INTEGRATIONS_BYOC.md`](./INTEGRATIONS_BYOC.md)

## Installation

```bash
pip install trendsagi            # client + agent tools
pip install "trendsagi[mcp]"     # adds the MCP server (Python 3.10+)
```

Create an API key in your TrendsAGI profile and export it:

```bash
export TRENDSAGI_API_KEY="your_api_key"
```

## Quick Start

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

## Use TrendsAGI from AI agents

Agents need fresh context about what people are paying attention to. The same twelve tools are available in every format below; they are **read-only by default**, and tools that change account state (`add_to_watchlist`, `update_recommendation`) are only exposed when you opt in with `allow_writes=True` / `--allow-writes`.

| Tool | What the agent gets |
| --- | --- |
| `list_trends` | Trending topics filtered by category or phrase, sorted by velocity, growth or volume |
| `list_trend_categories` | Valid category names |
| `search_trend_insights` | Trends and insights matching a theme |
| `get_trend` / `get_trend_analytics` | One trend and its volume time series |
| `get_trend_ai_insights` | Summary, key themes, sentiment, audience, marketing angles |
| `list_recommendations` | Evidence-backed actions with a decision brief |
| `list_crisis_events` | Reputation and crisis events for monitored topics |
| `list_watchlist` / `get_api_usage` | Watched topics and remaining daily quota |
| `add_to_watchlist` / `update_recommendation` | Write tools (opt-in) |

### Local MCP server (Claude Desktop, Claude Code, Cursor, VS Code)

Prefer to run it yourself, or need the opt-in write tools? The SDK ships the same server over stdio:

```bash
pip install "trendsagi[mcp]"
claude mcp add trendsagi --env TRENDSAGI_API_KEY=your_api_key -- trendsagi mcp
```

Or add it to any MCP client's JSON config (for example `claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "trendsagi": {
      "command": "trendsagi-mcp",
      "env": { "TRENDSAGI_API_KEY": "your_api_key" }
    }
  }
}
```

Then ask: *"What is trending in Technology this hour, and which of those topics fit our product launch?"*

### OpenAI function calling

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

Use `tools.openai_responses()` for the Responses API.

### Anthropic (Claude) tool use

```python
import json, os
import anthropic
from trendsagi import TrendsAGIClient, TrendsAGITools

tools = TrendsAGITools(TrendsAGIClient(api_key=os.environ["TRENDSAGI_API_KEY"]))
claude = anthropic.Anthropic()
messages = [{"role": "user", "content": "Which trending topics should our sports brand react to today?"}]

while True:
    reply = claude.messages.create(model="claude-sonnet-5-5", max_tokens=2048, tools=tools.anthropic(), messages=messages)
    messages.append({"role": "assistant", "content": reply.content})
    calls = [block for block in reply.content if block.type == "tool_use"]
    if not calls:
        print(next(block.text for block in reply.content if block.type == "text"))
        break
    messages.append({"role": "user", "content": [
        {"type": "tool_result", "tool_use_id": c.id, "content": json.dumps(tools.call(c.name, c.input))}
        for c in calls
    ]})
```

### LangChain

```python
from trendsagi import TrendsAGIClient, TrendsAGITools

langchain_tools = TrendsAGITools(TrendsAGIClient(api_key="...")).langchain()  # pip install "trendsagi[langchain]"
```

### Campaign-optimisation loop

A typical agent loop: `list_trends` (category you sell into, sorted by velocity) → `get_trend_analytics` (confirm it is still rising) → `get_trend_ai_insights` (audience and angle) → `list_recommendations` (evidence-backed action) → preview the change with a BYOC executor below → only then apply it. Tool errors come back as `{"error": ...}` instead of exceptions, so the model can read a rate limit or a missing argument and recover.

## BYOC Ad Execution

```python
import os
from trendsagi import TrendsAGIClient
from trendsagi.integrations import GoogleAdsExecutor

client = TrendsAGIClient(api_key=os.getenv("TRENDSAGI_API_KEY"))

# 1) Discover a real trend and read its cached insight
trends = client.get_trends(limit=5)
trend = next((item for item in trends.trends if item.id is not None), None)
if trend is None:
    raise RuntimeError("No trend is available in this window")
insight = client.get_ai_insights(trend_id=trend.id)
if not insight:
    raise RuntimeError("AI insight not ready yet")

# 2) Execute in your own runtime (credentials stay with you)
google = GoogleAdsExecutor(
    {
        "access_token": os.environ["GOOGLE_ADS_ACCESS_TOKEN"],
        "developer_token": os.environ["GOOGLE_ADS_DEVELOPER_TOKEN"],
    }
)

# 3) Preview only; inspect the result before any explicit execution
preview = google.apply_targeting(
    insight,
    customer_id="1234567890",
    campaign_id="9876543210",
    dry_run=True,
    strict_mode=True,
)
print(preview.response)
```

## Evidence-backed recommendations

Recommendations include an optional decision brief that explains why an action is
timely, the measured signals behind it, expected benefit, urgency, and concrete next
steps. The confidence score measures evidence completeness; it is not a prediction of
business outcomes.

```python
recommendations = client.get_recommendations(
    match_user_interests=True,
    priority="high",
    sort="priority",
    limit=10,
)

for recommendation in recommendations.recommendations:
    brief = recommendation.decision_brief
    if brief is None:
        # Compatible with API deployments that predate decision briefs.
        continue

    print(recommendation.title, brief.confidence.score, brief.why_now)
    if brief.actionable and brief.next_steps:
        print("Next step:", brief.next_steps[0])
    else:
        print("Verify first; missing:", ", ".join(brief.data_quality.missing_signals))
```

Use `actionable` and `data_quality` to degrade honestly when a trend is stale or
supporting signals are incomplete. The API returns HTTP 409 if a client attempts to
mark a recommendation `actioned` while its current brief is not actionable.

## Supported Integrations

- `GoogleAdsExecutor`
- `MetaAdsExecutor`
- `TikTokAdsExecutor`
- `LinkedInAdsExecutor`

All integrations support:
- runtime-supplied credentials
- deterministic idempotency keys
- dry-run previews (`dry_run=True`)
- strict validation (`strict_mode=True`)

## Core Endpoints Used by Integrations

- `GET /api/trends`
- `GET /api/trends/{trend_id}/ai-insights`
- `POST /api/trends/{trend_id}/ai-insights/generate`
- `GET /api/trends/ai-insights/status/{task_id}`
- `GET /api/intelligence/recommendations`

For full request/response contracts and all other endpoints, use the API docs link above.

The legacy crisis-event list and acknowledge/archive methods remain available for
accounts entitled to the existing crisis feature. The resilience beta's event
evidence, reviews, exports, source status, and location methods from version
0.10.0 have been withdrawn and are no longer supported by the current API.

## CLI

```bash
trendsagi mcp [--allow-writes]   # MCP server over stdio
```

### Scaffolder

```bash
# Docker template
trendsagi scaffold --type docker --output ./runner

# Terraform template
trendsagi scaffold --type terraform --output ./infra
```

## Error Handling

```python
from trendsagi import exceptions

try:
    client.get_trends(limit=5)
except exceptions.RateLimitError:
    print("Rate limited; retry with backoff")
except exceptions.AuthenticationError:
    print("Invalid API key")
```
