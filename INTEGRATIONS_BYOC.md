# BYOC Integrations Guide

This SDK supports customer-hosted ad execution where credentials are provided at runtime.

## Principle

- TrendsAGI API provides enriched insight signals.
- Your worker executes platform updates.
- Credentials stay in your environment and are never sent back to TrendsAGI.

## Recommended Runtime Pattern

1. Fetch trends + AI insights.
2. Validate safety gates:
   - `insight.brand_safety.level`
   - `insight.trend_metrics.commercial_intent`
3. Build payload with platform executor.
4. Run a dry run.
5. Execute with persistent run logs (idempotency key, resource IDs, payload hash, timestamp).

## Idempotency and Retries

- Every executor has `build_idempotency_key`.
- Reuse the same key for retries of the same run.
- Retry network/transient platform failures with exponential backoff.

## Rollback

Keep your own rollback journal:

- Prior targeting config snapshot
- Affected campaign/adset/adgroup IDs
- Execution metadata and request IDs

On rollback, restore previous targeting from the snapshot and annotate the run as rolled back.


## Preview an actual discovered trend

```python
import os
from trendsagi import TrendsAGIClient, GoogleAdsExecutor

client = TrendsAGIClient(os.environ["TRENDSAGI_API_KEY"], timeout=20)
trends = client.get_trends(limit=5)
trend = next((t for t in trends.trends if t.id is not None), None)
if trend is not None:
    insight = client.get_ai_insights(trend.id)
    if insight is not None:
        executor = GoogleAdsExecutor({
            "access_token": os.environ["GOOGLE_ADS_ACCESS_TOKEN"],
            "developer_token": os.environ["GOOGLE_ADS_DEVELOPER_TOKEN"],
        })
        preview = executor.apply_targeting(
            insight,
            customer_id=os.environ["GOOGLE_ADS_CUSTOMER_ID"],
            campaign_id=os.environ["GOOGLE_ADS_CAMPAIGN_ID"],
            dry_run=True,
            strict_mode=True,
        )
        print(preview)
```

The preview does not send an advertising mutation. Provider execution still requires valid permissions, identifiers, explicit approval in your own workflow and a rollback journal. A completeness or brand-safety score does not prove campaign suitability. Resilience events are reviewed separately and are not inputs to automatic audience creation or campaign changes.
