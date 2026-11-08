# TrendsAGI tool reference

All tools are read-only and return a JSON value in a text content block. A
tool-level failure arrives as `isError: true` with a JSON body; a protocol
failure arrives as a JSON-RPC error. Tool names, descriptions and argument
schemas in `tools/list` are authoritative for the connected account.

## Discovery and trends

| Tool | Use it for | Key arguments | Notes |
| --- | --- | --- | --- |
| `list_trends` | What is trending now, or around a brand, product or competitor | `category`, `search`, `sort_by` (`velocity`, `growth`, `volume`, `timestamp`, `name`; default `velocity`), `period` (`1h`, `24h`, `7d`, `30d`; default `24h`), `limit` (1-25; default 10) | `velocity` is the fastest-accelerating first. `volume` is the biggest audience right now. |
| `list_trend_categories` | Valid category names | none | Call before `list_trends` when the category name is uncertain. |
| `search_trend_insights` | Find trends by theme, product or phrase | `query` (required), `limit` (1-25) | Plan-gated: needs insight search. Use when the user describes a topic rather than naming a trend. |
| `get_trend` | One trend's current snapshot | `trend_id` (required) | Volume, velocity, growth, category. |
| `get_trend_analytics` | Is the trend rising, flat or fading? | `trend_id` (required), `period` (`24h`, `7d`, `30d`; default `7d`) | Returns a time series. Plan-gated: needs trend analytics. |
| `get_trend_ai_insights` | Audience, sentiment, themes and marketing angles | `trend_id` (required) | Plan-gated: needs trend insights. Returns `not_found` or null when no insight exists yet. |
| `get_trend_dossier` | The source-backed story behind a label: subject, timeline, channels, content landscape, brands and products | `trend_id` (required) | Plan-gated: needs insights access. Returns `not_found` when no dossier has been generated yet. Evidence, not a measurement. |
| `list_web_trends` | Labels found in an external trend list that may not be in the measured table yet | `limit` (1-25; default 10) | Discovery evidence only: no measured volume or velocity. `matched_trend_id` links to a measured trend when one exists. |

## Account intelligence

| Tool | Use it for | Key arguments | Notes |
| --- | --- | --- | --- |
| `list_recommendations` | The account's evidence-backed recommendations | `priority` (`low`, `medium`, `high`, `critical`, `all`), `status` (`new`, `viewed`, `actioned`, `dismissed`, `all`; default `new`), `recommendation_type`, `match_user_interests` (boolean), `limit` (1-10; default 5) | Plan-gated: needs recommendations. Each item carries a decision brief and evidence. |
| `list_crisis_events` | Reputation or crisis events on monitored topics | `status` (`active`, `resolved`, `all`; default `active`), `time_range` (`24h`, `7d`, `30d`; default `24h`), `limit` (1-25) | Plan-gated: needs crisis monitoring. Check before scaling spend on a brand. |
| `list_watchlist` | Topics the account watches and their alert conditions | none | Every plan. |
| `get_api_usage` | Remaining daily allowance and rate state | none | Call after a `429`, not on every turn. |

## SQL

| Tool | Use it for | Key arguments | Notes |
| --- | --- | --- | --- |
| `read_data_schema` | Tables, columns, rules and example queries for `execute_sql` | none | Call once per task, before writing SQL. |
| `execute_sql` | Filtering, joins, aggregation, counts, hourly series | `query` (one read-only `SELECT` or `WITH ... SELECT`, max 10,000 chars), `max_rows` (1-200 over MCP; default 50) | Results stop at `max_rows` and may be marked truncated. Use SQL instead of chaining narrow tools for comparisons. |

## Capability checks

| Tool | Use it for | Key arguments | Notes |
| --- | --- | --- | --- |
| `find_capability` | A task no other tool covers: alerts, exports, connecting an ad account, in-app settings | `goal` (a few words, max 200 chars) | Returns the tools that cover the task, or the page in the TrendsAGI app where the user does it. |

## Return shapes

- Most tools return the API object directly: lists use keys such as `trends`,
  `categories`, `recommendations` or `crisis_events`; single-item tools return
  the object.
- SQL returns `columns`, `rows`, `row_count`, `truncated`, `truncated_reason`,
  `tables` and `elapsed_ms`.
- A tool error returns `{"error": "...", "detail": "...", "hint": "..."}` with
  `isError: true`. Read `hint` before retrying.
- Large results are replaced with `result_truncated`, `result_preview` and a
  `hint`. Narrow the request; do not ask for the same result again unchanged.

## Local SDK-only read tools

These exist in the Python SDK's `TrendsAGITools` registry and its local stdio
server. They are not part of the hosted connection.

| Tool | Use it for | Key arguments | Notes |
| --- | --- | --- | --- |
| `get_search_demand` | Relative search-interest series and related queries | `trend_id` (required), `geo` (default `US`) | Interest is a 0-100 index, not absolute search volume. |
| `get_brand_momentum` | Brands visible in the coverage and their movement | `trend_id` (required), `window` (`24h`, `7d`, `30d`; default `7d`) | Share of coverage, not market share. |
| `get_trend_creators` | Accounts posting most about the trend | `trend_id` (required) | Posting activity, not influence. |
| `ask_trend` | A grounded answer about one trend | `trend_id`, `question` | Returns citations; `grounded=false` when evidence is insufficient. |
| `get_social_evidence` | The stored Social Evidence report | `trend_id` (required) | Free to read; `not_found` when no report exists yet. |
| `get_social_evidence_credits` | The Social Evidence credit balance | none | Free; does not consume a credit. |

## Local SDK-only write tools

`add_to_watchlist`, `update_recommendation`, `enrich_trend`,
`run_social_evidence` and `create_social_evidence_checkout` exist only in the
local Python SDK's stdio server when it is started with `--allow-writes`. They
are not part of the hosted connection and must never be described as available
here. `enrich_trend` and `run_social_evidence` reserve credits; the checkout
tool only returns a Stripe URL the user must open.
