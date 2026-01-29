# TrendsAGI Official Python Client

[![PyPI Version](https://img.shields.io/pypi/v/trendsagi.svg)](https://pypi.org/project/trendsagi/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python Versions](https://img.shields.io/pypi/pyversions/trendsagi.svg)](https://pypi.org/project/trendsagi/)

The official Python client for [TrendsAGI](https://trendsagi.com). Designed to power AI agents with real-time market intelligence, trend contexts, and actionable insights.

## Features

- **Agentic Context**: Inject real-time trend and financial data into your agent's context window.
- **Active Research**: Trigger AI-powered deep dives and insight generation on-demand.
- **Actionable Intelligence**: Retrieve and act on high-priority recommendations.
- **Live Streaming**: WebSocket support for real-time financial and trend events.
- **Type-Safe**: Complete Pydantic models for robust agent integration.

## Installation

```bash
pip install trendsagi
```

## Quick Start: Agent Context Check

Give your agent immediate awareness of the current market landscape.

```python
import os
from trendsagi import TrendsAGIClient, APIError

# Load API key
client = TrendsAGIClient(api_key=os.getenv("TRENDSAGI_API_KEY"))

try:
    # 1. Get Top Trends Context
    trends = client.get_trends(limit=5, period='24h')
    print("--- Current Top Trends ---")
    for trend in trends.trends:
        print(f"{trend.name}: Vol={trend.volume}, Velocity={trend.average_velocity:.1f}/hr")

    # 2. Get Financial Context (Localized)
    finance = client.get_financial_data(timezone="America/New_York")
    print(f"\n--- Market Sentiment: {finance.market_sentiment.sentiment} ---")
    
except APIError as e:
    print(f"Error: {e.error_detail}")
```

## Agentic Workflows

TrendsAGI is built to support the **Context -> Research -> Action** loop for autonomous agents.

### 1. Context & Discovery
Equip your agent to "see" what is happening right now.

```python
# Search for specific topic contexts
ai_trends = client.get_trends(search="artificial intelligence", limit=3)

# Get detailed analytics for a specific trend to understand stability
if ai_trends.trends:
    trend_id = ai_trends.trends[0].id
    analytics = client.get_trend_analytics(trend_id=trend_id, period="7d")
    print(f"Analaryzing trend stability: {len(analytics.data)} data points")
```

### 2. Deep Research
Access AI-powered insights for deeper analysis on specific trends.

```python
# Retrieve cached AI-powered insights
insights = client.get_ai_insights(trend_id=trend_id)

if insights:
    print(f"Key Themes: {insights.key_themes}")
    print(f"Sentiment: {insights.sentiment_summary}")
    print(f"Target Audience: {insights.content_brief.target_audience_segments}")
else:
    print("No insights available for this trend yet. Insights must be generated via the dashboard.")
```

### 3. Context Intelligence Suite
Manage complex context for your agents by organizing specifications, plans, and reference materials.

```python
# 1. Create a Context Project
project = client.create_context_project(
    name="Agent Alpha: Strategy", 
    description="Product specs and tech stack for the new agent loop."
)

# 2. Add Context Items (Text or Files)
client.create_context_item(
    project_id=project.id,
    item_type="product_spec",
    name="Feature Roadmap",
    content="Implement a multi-step orchestration loop with grounding."
)

# 3. Query Context for Agent Prompts
# This retrieves full content for all relevant items in a project
context_items = client.query_context(project_id=project.id, search="Roadmap")

for item in context_items:
    print(f"\n--- {item.name} ---\n{item.content}")
```

### 4. Action & Recommendations
The system generates high-level strategy recommendations that your agent can process and execute.

```python
# Get high-priority actions
recs = client.get_recommendations(priority="high", status="new")

for rec in recs.recommendations:
    print(f"Action: {rec.title} (Type: {rec.type})")
    
    # Report back to the system
    client.perform_recommendation_action(
        recommendation_id=rec.id, 
        action="completed", 
        feedback="Agent generated content based on this recommendation."
    )
```

## Advanced Agent Configuration

The client supports advanced configuration for agent intelligence, retrieval, and safety:

```python
agent = client.create_agent(
    name="Research Assistant",
    description="Deep research agent with safety guardrails",
    
    # Query Reformulation
    enable_query_expansion=True,
    query_expansion_prompt="Expand queries to include synonym technical terms.",
    
    # Retrieval Settings
    top_k_retrieved_chunks=100,
    lexical_alpha=0.4,
    semantic_alpha=0.6,
    
    # Reranking
    enable_rerank=True,
    reranker_score_threshold=0.7,
    
    # Safety (Model Armor)
    safety_prompt_injection="high",
    safety_malicious_urls="high",
    safety_csam="high"
)
```

## Real-Time Streaming

For agents that need to react instantly to market moves.

```python
import asyncio

async def watch_market():
    # Connect to the financial data stream
    print("Listening for market events...")
    async for message in client.finance_stream():
        # 'message' is a JSON string
        print(f"Event: {message}")

async def watch_trends():
    # Track specific topics
    print("Tracking AI trends...")
    async for message in client.trends_stream(trend_names=["AI", "LLMs"]):
        print(f"Trend Update: {message}")

# Run within your async event loop
# asyncio.run(watch_market())
```

## Error Handling

```python
from trendsagi import exceptions

try:
    client.get_trends()
except exceptions.RateLimitError as e:
    print("Rate limited. Slow down and retry.")
except exceptions.AuthenticationError:
    print("Check your API Key")
```

## Throttling and Retries

If you want the SDK to automatically retry on 429 responses, enable it at initialization.

```python
import os
client = TrendsAGIClient(
    api_key=os.getenv("TRENDSAGI_API_KEY"),
    enable_retry_on_rate_limit=True,
    max_retries=3,
    max_retry_wait=10.0,
    retry_backoff_factor=0.5,
    retry_jitter=0.1,
)
```

Retries are only applied to `429 Too Many Requests` and honor `Retry-After` when provided.
By default, retries are disabled to avoid changing behavior for existing clients.

## Rate Limits & Throttling

Responses include standard `X-RateLimit-*` headers for usage limits, plus per-second throttling headers.

**Common headers**
- `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`
- `X-RateLimit-Limit-Second`, `X-RateLimit-Remaining-Second`, `X-RateLimit-Reset-Second`
- `Retry-After` (when throttled)

**Per-second throttle (burst protection)**

| Plan | Requests / Second |
|------|-------------------|
| **Developer** | 2 |
| **Advantage** | 10 |
| **Scale** | 50 |
| **Enterprise** | 200 |

Unauthenticated requests are throttled separately.

## Support & Resources

- **Full API Docs**: [trendsagi.com/api-docs](https://trendsagi.com/api-docs)
- **Issues**: [GitHub Issues](https://github.com/TrendsAGI/TrendsAGI/issues)
- **Contact**: contact@trendsagi.com

## License

MIT License - see [LICENSE](LICENSE) for details.
