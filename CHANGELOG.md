# Changelog

All notable changes to the official TrendsAGI Python client are documented here.

## [0.10.0] - 2026-09-24 release candidate

- Includes the previously unreleased 0.9.0 recommendation changes below; PyPI's prior release was 0.8.1.
- Adds typed crisis details, source evidence, append-only reviews, JSON/HTML exports, source health and explicit location preferences.
- Adds optional evidence/freshness/review models compatible with older payloads.
- Adds configurable positive HTTP timeouts, malformed-response handling and compatible authorization/capability exceptions.
- Audits every SDK HTTP call against backend routes and supplies an OpenAPI contract; legacy financial-data is explicitly unavailable.
- Replaces fixed trend IDs with discovery examples and provides tested server-side JavaScript HTTP examples.
- Keeps BYOC executors and existing exception base classes. Advertising examples use previews.
- Correctly identifies a newly created monitoring interest in the backend's unordered list response.
- Resilience is beta, with limited official-source coverage; completeness is not probability and HTML export is not offline inference.

## [0.9.0] - Unreleased changes included in 0.10.0

### Added

- Typed recommendation decision briefs with supporting evidence, evidence completeness, expected benefit, urgency, data quality, and next steps.
- Explicit recommendation ordering with `priority` (default) and `newest` modes.

### Changed

- Recommendation requests now default to 10 new items in priority order and cap page
  size at the API maximum of 100.
- Recommendation type, source-trend, priority, status, interest-match, and ordering
  filters are validated and serialized consistently with the API contract.
- Recommendation actions now validate IDs, workflow states, exclusive payload fields,
  and the 500-character feedback limit before making a network request.
- `source_trend_id` accepts both string and integer values for compatibility across API
  record generations.

### Compatibility

- `decision_brief` is optional, so responses from older TrendsAGI API deployments remain
  valid in SDK 0.9.0.
