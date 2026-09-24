# TrendsAGI Python SDK

Official Python access to TrendsAGI paid-media intelligence and operational resilience.

Install:

```sh
python -m pip install --upgrade trendsagi
```

Python 3.8+ is supported. Configure `TRENDSAGI_API_KEY` with your own TrendsAGI API key. A PyPI publishing token is not a TrendsAGI API key.

- [API documentation](https://trendsagi.com/api-docs)
- [OpenAPI contract](https://trendsagi.com/openapi.json)
- [Resilience methodology](https://trendsagi.com/research/resilience)
- [BYOC advertising execution](INTEGRATIONS_BYOC.md)

## Paid media: inspect an actual trend

```python
import os
from trendsagi import TrendsAGIClient

client = TrendsAGIClient(api_key=os.environ["TRENDSAGI_API_KEY"], timeout=20)
trends = client.get_trends(limit=5)
if not trends.trends:
    print("No trends available in this window.")
else:
    trend = next((item for item in trends.trends if item.id is not None), None)
    if trend is not None:
        insight = client.get_ai_insights(trend.id)
        print(insight if insight else "No cached insight yet.")
```

This example reads cached data. Insight generation is a separate queued operation subject to your entitlement and usage limits. Recommendation scores using `evidence_completeness_v1` measure available evidence, not campaign uplift or event probability.

Google, Meta, TikTok and LinkedIn executors remain BYOC: credentials stay in your runtime. Start with `dry_run=True` and `strict_mode=True`. Inspect the preview before explicitly executing a change. See the integration guide for required account identifiers and provider permissions.

## Resilience — Beta

The resilience methods require the existing crisis-functionality entitlement. An API key does not bypass subscription access, ownership checks or usage accounting.

```python
import os
from pathlib import Path
from trendsagi import TrendsAGIClient

client = TrendsAGIClient(os.environ["TRENDSAGI_API_KEY"], timeout=20)
events = client.get_crisis_events(status="all", time_range="7d")
if not events.events:
    print("No matching events. Review your location and keyword interests.")
else:
    event = client.get_crisis_evidence(events.events[0].id)
    print(event.title, event.freshness, event.review_status)
    for source in event.source_refs:
        print(source.source_id, source.observed_at, source.source_url)
    for limitation in event.limitations:
        print("Limitation:", limitation)
    Path("evidence.html").write_text(
        client.export_crisis_event(event.id, format="html"), encoding="utf-8"
    )
```

HTML exports are dated, self-contained evidence snapshots. They work offline but do not perform offline AI inference or update offline.

To opt into official-source matching, set a location using `set_resilience_location("Nottinghamshire")` and maintain an active keyword interest such as `flood`. Both must match. An empty location disables matching. Inspect `get_resilience_sources()` for availability and coverage.

After reviewing evidence, append a human assessment explicitly:

```python
reviewed = client.review_crisis_event(
    event.id,
    assessment="unconfirmed",
    rationale="The source reports an event; impact on our operation is not established.",
    evidence_version=event.evidence_version,
)
```

Assessments are `unconfirmed`, `supported` or `disputed`. A changed evidence version returns HTTP 409; refresh before reviewing again. Reviews preserve history and are separate from acknowledge/archive/reopen actions.

Official sources initially cover Environment Agency flood warnings in England and USGS global magnitude 4.5+ earthquakes. Social signals and heuristic severity do not establish an incident. One publisher is not independent corroboration.

## Errors and compatibility

```python
from trendsagi import exceptions

try:
    sources = client.get_resilience_sources()
except exceptions.AuthorizationError:
    print("This account lacks the necessary entitlement.")
except exceptions.ConflictError:
    print("Refresh the evidence before recording a review.")
except exceptions.RateLimitError:
    print("Respect the usage limit and retry later.")
except exceptions.CapabilityUnavailableError:
    print("This capability is unavailable; do not poll indefinitely.")
except exceptions.TrendsAGIError as error:
    print(type(error).__name__)
```

The default HTTP timeout is 20 seconds and is configurable. Rate-limit retries are opt-in and bounded. New event fields are optional; legacy responses without evidence remain readable. `CapabilityUnavailableError` retains compatibility with `MaintenanceError`, and authorization errors remain `APIError` subclasses.

The legacy financial-data method remains for compatibility but its backend capability is unavailable. It is not an active product feature.

## JavaScript / TypeScript

Use standard HTTPS with `X-API-Key`; there is no maintained npm SDK represented by this release. Tested examples are in [examples/resilience.mjs](examples/resilience.mjs). Never ship account API keys in public browser code.

## Deployment and data

This SDK does not establish UK-only hosting, security certification, defence accreditation or permission to redistribute source content. Consult the current [privacy](https://trendsagi.com/privacy), [security](https://trendsagi.com/security), and source licensing information. Preserve tenant isolation and source restrictions when exporting.

## Development

```sh
python -m unittest discover -s tests -v
python -m build
python -m twine check dist/*
```

See [CHANGELOG.md](CHANGELOG.md) for release changes. Supported API methods and known unavailable capabilities are recorded in the contract audit.
