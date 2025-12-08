# TrendsAGI Official Python Client

[![PyPI Version](https://img.shields.io/pypi/v/trendsagi.svg)](https://pypi.org/project/trendsagi/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python Versions](https://img.shields.io/pypi/pyversions/trendsagi.svg)](https://pypi.org/project/trendsagi/)

The official Python client for [TrendsAGI](https://trendsagi.com). Designed to power AI agents with real-time market intelligence, trend contexts, and actionable insights.

## Features

- **Agentic Context**: Inject real-time trend and financial data into your agent's context window.
- **Active Research**: Trigger AI-powered deep dives and insight generation on-demand.
- **Monitoring & Alerts**: Track specific X (Twitter) users and receive crisis alerts.
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
Agents can request deeper analysis when they spot something interesting.

```python
# Check if insights already exist
insights = client.get_ai_insights(trend_id=trend_id)

if not insights:
    # Trigger an asynchronous research task
    task = client.generate_ai_insights(trend_id=trend_id)
    print(f"Research task started: {task.task_id}")
    
    # In a real agent loop, you would poll this status or use a callback
    # status = client.get_insight_generation_status(task.task_id)
else:
    print(f"Key Themes: {insights.key_themes}")
    print(f"Audience: {insights.content_brief.target_audience_segments}")
```

### 3. Monitoring (X/Twitter)
Track key opinion leaders or entities relevant to your agent's goal.

```python
# Add a user to the monitoring list
user = client.create_tracked_x_user(handle="elonmusk", notes="Monitor for tech announcements")

# Force a refresh of the analysis (consuming a credit) if critical
fresh_analysis = client.refresh_x_user_analysis(entity_id=user.id, force_refresh=True)
print(f"Latest breakdown: {fresh_analysis.entity.recent_post_analysis.summary}")
```

### 4. Action & Recommendations
The system generates high-level strategy recommendations that your agent can process and execute.

```python
# Get high-priority actions
recs = client.get_recommendations(priority="high", status="new")

for rec in recs.recommendations:
    print(f"Action: {rec.title} (Type: {rec.type})")
    
    # Agent decides to execute the action...
    # ... execution logic here ...
    
    # Report back to the system
    client.perform_recommendation_action(
        recommendation_id=rec.id, 
        action="completed", 
        feedback="Agent generated content based on this recommendation."
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
    print(f"Slow down! Retry in {e.retry_after}s") # Handle backoff
except exceptions.AuthenticationError:
    print("Check your API Key")
```

## Rate Limits

Responses include `X-RateLimit-*` headers.

| Plan | API Access | Daily Calls (Approx) | Live Streaming |
|------|------------|----------------------|----------------|
| **Signal** | ❌ No | - | ❌ |
| **Advantage** | ✅ Yes | ~10k | ❌ |
| **Scale** | ✅ Yes | ~25k | ✅ Available |
| **Enterprise** | ✅ Yes | Unlimited | ✅ Available |

## Support & Resources

- **Full API Docs**: [trendsagi.com/api-docs](https://trendsagi.com/api-docs)
- **Issues**: [GitHub Issues](https://github.com/TrendsAGI/TrendsAGI/issues)
- **Contact**: contact@trendsagi.com

## License

MIT License - see [LICENSE](LICENSE) for details.