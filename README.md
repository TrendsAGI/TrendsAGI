# TrendsAGI Official Python Client

[![PyPI Version](https://img.shields.io/pypi/v/trendsagi.svg)](https://pypi.org/project/trendsagi/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python Versions](https://img.shields.io/pypi/pyversions/trendsagi.svg)](https://pypi.org/project/trendsagi/)

The official Python client for the [TrendsAGI API](https://trendsagi.com), providing access to real-time trend data, AI-powered insights, market intelligence, and live streaming capabilities.

## Features

- **Trends & Insights**: Real-time trend data with analytics (volume, velocity, stability)
- **AI-Powered Analysis**: Deep insights, sentiment analysis, and content recommendations
- **Intelligence Suite**: Market tracking, crisis monitoring, custom reports, and recommendations
- **Live Streaming**: WebSocket connections for real-time financial and trend data
- **User Management**: Topic interests, notifications, and alert configuration
- **Full Type Support**: Complete Pydantic models with IDE autocompletion

## Installation

```bash
pip install trendsagi
```

## Quick Start

```python
import os
from trendsagi import TrendsAGIClient, APIError

# Load API key from environment variable (recommended)
client = TrendsAGIClient(api_key=os.getenv("TRENDSAGI_API_KEY"))

try:
    # Get trending topics with new analytics
    trends = client.get_trends(limit=5, period='24h')
    
    for trend in trends.trends:
        print(f"Trend: {trend.name}")
        print(f"  Volume: {trend.volume}")
        print(f"  Overall Trend: {trend.overall_trend}")
        print(f"  Avg Velocity: {trend.average_velocity:.2f} posts/hr")
        print(f"  Stability: {trend.trend_stability:.2f}")
        
except APIError as e:
    print(f"API Error ({e.status_code}): {e.error_detail}")
```

## Core Functionality

### Trends & Analytics

```python
# Find trends about AI and get detailed information
ai_trends = client.get_trends(search="artificial intelligence", limit=3)

if ai_trends.trends:
    trend = ai_trends.trends[0]  # Get the top AI trend
    print(f"Working with trend: {trend.name}")
    
    # Get detailed trend information
    trend_details = client.get_trend_details(trend_id=trend.id)
    print(f"Category: {trend_details.category}")
    print(f"Sample tweets: {len(trend_details.tweets)}")
    
    # Get historical analytics for this trend
    analytics = client.get_trend_analytics(trend_id=trend.id, period="7d")
    print(f"Analytics over {len(analytics.data)} data points")
    
    # Get AI insights for this trend
    insights = client.get_ai_insights(trend_id=trend.id)
    print(f"Sentiment: {insights.sentiment_category}")
    print(f"Key Themes: {insights.key_themes}")
```

### Intelligence Suite

```python
# Search trends by AI-generated insights
results = client.search_insights(
    key_theme_contains="sustainability",
    sentiment_category="positive"
)

# Generate custom reports
report = client.generate_custom_report({
    "dimensions": ["trend_category"],
    "metrics": ["sum_volume"],
    "time_period": "7d"
})

# Get actionable recommendations
recommendations = client.get_recommendations(priority="high")
for rec in recommendations.recommendations:
    print(f"- {rec.title}")

# Track X (Twitter) users
user = client.create_tracked_x_user(
    handle="elonmusk",
    name="Elon Musk",
    notes="Tech industry leader"
)

# Refresh user analysis
analysis = client.refresh_x_user_analysis(
    entity_id=user.id, 
    force_refresh=True
)
print(f"Latest analysis: {analysis.entity.recent_post_analysis.summary}")
```

### Deep Analysis & Crisis Monitoring

```python
# Perform deep AI analysis on any topic
analysis = client.perform_deep_analysis(
    query="What are the primary concerns about AI in healthcare for 2025?"
)
print(analysis.executive_summary_and_key_findings.summary)

# Monitor crisis events
events = client.get_crisis_events(status="active")
for event in events.events:
    print(f"[{event.severity.upper()}] {event.title}")
```

### Financial Intelligence

```python
# Get consolidated financial data
financial_data = client.get_financial_data()

# Market sentiment
if financial_data.market_sentiment:
    print(f"Market: {financial_data.market_sentiment.sentiment_label}")

# Recent earnings reports
for report in financial_data.earnings_reports:
    print(f"{report.company_name}: EPS {report.eps_actual} vs {report.eps_estimate}")

# IPO filings
for ipo in financial_data.ipo_filings_news:
    print(f"{ipo.company_name} IPO expected: {ipo.expected_date}")
```

### User Management

```python
# Create topic interest with alerts
interest = client.create_topic_interest(
    keyword="artificial intelligence",
    alert_condition_type="volume_threshold",
    volume_threshold_value=5000,
    send_email_alerts=True
)

# Get recent notifications
notifications = client.get_recent_notifications(limit=10)
print(f"Unread: {notifications.unread_count}")

# Mark notifications as read
client.mark_notifications_read(ids=[100, 101])
```

### Live Streaming (WebSockets)

```python
import asyncio
import websockets
import json

# Real-time financial data stream
async def stream_financial_data():
    uri = f"wss://api.trendsagi.com/ws/finance-live?token={API_KEY}"
    
    async with websockets.connect(uri) as websocket:
        print("Connected to financial live stream")
        while True:
            message = await websocket.recv()
            data = json.loads(message)
            
            if data["type"] == "new_earnings_report":
                print(f"New earnings: {data['payload']['company']}")

# Real-time trend data stream
async def stream_trend_data():
    # Subscribe to specific trends
    trends = "AI,Crypto,Web3"
    uri = f"wss://api.trendsagi.com/ws/trends-live?token={API_KEY}&trends={trends}"
    
    async with websockets.connect(uri) as websocket:
        print("Connected to trends live stream")
        while True:
            message = await websocket.recv()
            trend_data = json.loads(message)
            print(f"{trend_data['trend_name']}: {trend_data['volume']} posts")

# Run the streams
asyncio.run(stream_financial_data())
```

## Error Handling

The client provides specific exceptions for different error types:

```python
from trendsagi.exceptions import (
    TrendsAGIError,          # Base exception
    AuthenticationError,     # 401 errors
    NotFoundError,          # 404 errors
    RateLimitError,         # 429 errors
    APIError               # General API errors
)

try:
    response = client.get_trends()
except AuthenticationError:
    print("Invalid API key")
except RateLimitError as e:
    print(f"Rate limit hit. Retry after: {e.retry_after}s")
except NotFoundError:
    print("Resource not found")
except APIError as e:
    print(f"API error {e.status_code}: {e.error_detail}")
```

## Rate Limits & Plans

Rate limits vary by subscription plan and endpoint type. The system uses endpoint-specific limits optimized for different use cases.

| Endpoint Category | Signal | Advantage | Scale | Enterprise |
|-------------------|--------|-----------|-------|------------|
| **API Access** | ❌ Not Available | ✅ Available | ✅ Available | ✅ Available |
| **General API Calls** | - | 300/hour | 1,500/hour | Unlimited |
| **Trends List** | - | 750/hour | 1,500/hour | Unlimited |
| **AI Insights Search** | - | 200/hour | 750/hour | Unlimited |
| **Analytics** | - | 300/hour | 1,500/hour | Unlimited |
| **Dashboard** | 180/hour | 360/hour | 720/hour | Unlimited |
| **Login/Auth** | 30/hour | 75/hour | 150/hour | Unlimited |
| **Intelligence Features** | - | 300/hour | 1,000/hour | Unlimited |
| **Financial Data** | - | 120/hour | 600/hour | Unlimited |
| **User Management** | 300/hour | 600/hour | 1,000/hour | Unlimited |
| **Live Streaming** | ❌ | ❌ | ✅ Available | ✅ Available |

### Rate Limit Headers

All API responses include rate limit information:
- `X-RateLimit-Limit`: Your current limit for this endpoint
- `X-RateLimit-Remaining`: Requests remaining in current window
- `X-RateLimit-Reset`: Unix timestamp when the limit resets

## API Documentation

For complete API reference, including all endpoints, parameters, and response schemas:

**[View Full API Documentation →](https://trendsagi.com/api-docs)**

## Plan Features by Tier

Different features are available based on your subscription:

### Signal Plan
- Basic trends access via web dashboard
- Limited history (7 days)
- 5 topic interests
- Basic reporting (10K row limit)
- CSV exports only

### Advantage Plan
- Full API access (10K calls/day)
- 30-day history
- 25 topic interests  
- Advanced insights and search
- Priority support
- Unlimited reporting rows
- 100 deep analysis queries/day

### Scale Plan
- Enhanced API access (25K calls/day)
- 90-day history
- 100 topic interests
- Crisis monitoring
- Live streaming access
- Cloud exports
- Slack notifications
- Video generation
- 1,000 deep analysis queries/day

### Enterprise Plan
- Unlimited API access
- Unlimited history
- Unlimited topic interests
- Custom integrations
- Dedicated support & SLA
- All premium features
- Unlimited deep analysis

## Support

- **API Documentation**: [trendsagi.com/api-docs](https://trendsagi.com/api-docs)
- **Support**: contact@trendsagi.com
- **Issues**: [GitHub Issues](https://github.com/TrendsAGI/TrendsAGI/issues)

## License

MIT License - see [LICENSE](LICENSE) file for details.