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

