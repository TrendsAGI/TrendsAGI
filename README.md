# TrendsAGI Python Utilities

[![PyPI Version](https://img.shields.io/pypi/v/trendsagi.svg)](https://pypi.org/project/trendsagi/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python Versions](https://img.shields.io/pypi/pyversions/trendsagi.svg)](https://pypi.org/project/trendsagi/)

## About

`trendsagi` provides:

- ad-platform execution helpers for Google, Meta, TikTok, and LinkedIn
- deterministic idempotency-key generation
- scaffold commands for Docker and Terraform templates

This package does not include a TrendsAGI HTTP API client.

## Installation

```bash
pip install trendsagi
```

## Quick Start

```python
from trendsagi import AIInsight
from trendsagi.integrations import GoogleAdsExecutor

insight = AIInsight.model_validate(
    {
        "trend_id": 123,
        "key_themes": ["running shoes", "marathon prep"],
        "audience_injection": {
            "interest_keywords": ["running shoes"],
            "negative_keywords": ["cheap"],
            "demographics": {"regions": ["US"]},
        },
    }
)

google = GoogleAdsExecutor(
    {
        "access_token": "YOUR_ACCESS_TOKEN",
        "developer_token": "YOUR_DEVELOPER_TOKEN",
    }
)

result = google.apply_targeting(
    insight,
    customer_id="1234567890",
    campaign_id="9876543210",
    dry_run=True,
)

print(result.idempotency_key)
```

## CLI Scaffolder

```bash
trendsagi scaffold --type docker --output-dir ./runner
trendsagi scaffold --type terraform --output-dir ./infra
```
