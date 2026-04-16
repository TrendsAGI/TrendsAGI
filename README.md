# TrendsAGI Official Python Client

[![PyPI Version](https://img.shields.io/pypi/v/trendsagi.svg)](https://pypi.org/project/trendsagi/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python Versions](https://img.shields.io/pypi/pyversions/trendsagi.svg)](https://pypi.org/project/trendsagi/)

## About
Connect your paid social and search workflows to live market signals.

`trendsagi` is a BYOC-first SDK: TrendsAGI provides intelligence (`/api/trends`, `/api/trends/{id}/ai-insights`), and you execute Google/Meta/TikTok/LinkedIn updates from your own infrastructure with runtime credentials.

## Plan Notes (API Access)
- Developer plan includes:
  - 1 API integration connection
  - 100 API calls/day included
  - Overage billing above included daily usage
- Advantage/Scale unlock higher daily API limits, more keys, and expanded team workflows.

## Resources
- API Docs: [https://trendsagi.com/api-docs](https://trendsagi.com/api-docs)
- Endpoint Reference: [https://trendsagi.com/api-docs#endpoints](https://trendsagi.com/api-docs#endpoints)
- BYOC Integrations Guide (repo): [`INTEGRATIONS_BYOC.md`](./INTEGRATIONS_BYOC.md)

## JavaScript / TypeScript SDK

This repository now also contains the JavaScript/TypeScript SDK package source in:

- [`javascript/`](./javascript)

It ships as the npm package `trendsagi`, with Python parity method names, BYOC ad executors, and a matching `trendsagi scaffold` CLI.

## Installation

```bash
pip install trendsagi
```

## Quick Start (BYOC Execution)

```python
import os
from trendsagi import TrendsAGIClient
from trendsagi.integrations import GoogleAdsExecutor

client = TrendsAGIClient(api_key=os.getenv("TRENDSAGI_API_KEY"))

# 1) Read intelligence
insight = client.get_ai_insights(trend_id=123)
if not insight:
    raise RuntimeError("AI insight not ready yet")

# 2) Execute in your own runtime (credentials stay with you)
google = GoogleAdsExecutor(
    {
        "access_token": os.environ["GOOGLE_ADS_ACCESS_TOKEN"],
        "developer_token": os.environ["GOOGLE_ADS_DEVELOPER_TOKEN"],
    }
)

# 3) Strict mode: fail fast on weak payloads / missing required IDs
google.apply_targeting(
    insight,
    customer_id="1234567890",
    campaign_id="9876543210",
    strict_mode=True,
)
```

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

For full request/response contracts and all other endpoints, use the API docs link above.

## CLI Scaffolder

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
