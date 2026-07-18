# Changelog

All notable changes to the official TrendsAGI Python client are documented here.

## [0.9.0] - Unreleased

### Added

- Typed recommendation decision briefs with supporting evidence, evidence-completeness
  confidence, expected benefit, urgency, data quality, and next steps.
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
