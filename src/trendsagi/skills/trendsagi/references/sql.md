# Read-only SQL

`execute_sql` is for questions that need filtering, joins, aggregation or a
time series. It is not a replacement for the narrow tools. Call
`read_data_schema` once per task before writing SQL; the schema it returns is
authoritative.

## Rules

- Send one read-only `SELECT`, or `WITH ... SELECT`. No writes, DDL, multiple
  statements or schema prefixes.
- PostgreSQL syntax. Common aggregates, window functions, date/time, string,
  math and jsonb functions work. Unknown functions are rejected by name.
- `volume`, `previous_volume` and `growth_pct` are `NULL` when not measured.
  `NULL` is never zero; add `NULLS LAST` when sorting.
- Timestamps are UTC `timestamptz`. Use `now() - interval '24 hours'` (or
  `'7 days'`, `'30 days'`).
- Queries time out after 5 seconds. Filter `trend_snapshots` by `trend_id` or a
  time window.
- `max_rows` is 1-200 over MCP (default 50). Results may be marked truncated.
  Aggregate in SQL instead of fetching raw rows.
- `watchlist`, `recommendations` and `crisis_events` only contain the
  authenticated account's rows.

## Tables

| Table | What it holds | Plan gate |
| --- | --- | --- |
| `trends` | One row per topic with the newest volume, growth, velocity, category and timestamps | Every plan |
| `trend_snapshots` | Every reading over the last 90 days, the series behind `get_trend_analytics` | Trend analytics |
| `trend_categories` | Category names and trend counts | Every plan |
| `trend_insights` | Stored AI insight per trend: sentiment, themes, content brief, targeting | Trend insights |
| `watchlist` | The account's watched keywords and alert conditions | Every plan |
| `recommendations` | The account's recommendations and decision briefs | Recommendations |
| `crisis_events` | Reputation or crisis events on monitored topics | Crisis monitoring |

Use `trends.id` to join to `trend_snapshots.trend_id` and
`trend_insights.trend_id`. `trends.category` matches `trend_categories.name`.

## Example queries

**Fastest risers right now**

```sql
SELECT id, name, category, volume, growth_pct, velocity_per_hour
FROM trends
WHERE last_seen_at > now() - interval '24 hours' AND volume IS NOT NULL
ORDER BY velocity_per_hour DESC NULLS LAST
LIMIT 20
```

**Category growth this week**

```sql
SELECT category, count(*) AS trends,
       round(avg(growth_pct)::numeric, 1) AS avg_growth_pct
FROM trends
WHERE last_seen_at > now() - interval '7 days' AND growth_pct IS NOT NULL
GROUP BY category
ORDER BY avg_growth_pct DESC
```

**Brand or competitor mentions**

```sql
SELECT id, name, volume, growth_pct, last_seen_at
FROM trends
WHERE name ILIKE '%nvidia%'
  AND last_seen_at > now() - interval '30 days'
ORDER BY last_seen_at DESC
LIMIT 20
```

**Hourly volume for one trend**

```sql
SELECT date_trunc('hour', observed_at) AS hour, max(volume) AS volume
FROM trend_snapshots
WHERE trend_id = 1359
  AND observed_at > now() - interval '7 days'
GROUP BY 1
ORDER BY 1
```

**Velocity at each reading**

```sql
SELECT observed_at, volume,
       (volume - lag(volume) OVER w) /
       NULLIF(extract(epoch FROM observed_at - lag(observed_at) OVER w) / 3600, 0)
         AS velocity_per_hour
FROM trend_snapshots
WHERE trend_id = 1359 AND volume IS NOT NULL
WINDOW w AS (ORDER BY observed_at)
ORDER BY observed_at
```

**Watchlist matches**

```sql
SELECT w.keyword, t.id, t.name, t.volume, t.growth_pct
FROM watchlist w
JOIN trends t ON t.name ILIKE '%' || w.keyword || '%'
WHERE t.last_seen_at > now() - interval '7 days'
ORDER BY t.velocity_per_hour DESC NULLS LAST
LIMIT 50
```

**Themes and sentiment behind today's fastest risers**

```sql
SELECT t.name, i.sentiment_category, i.key_themes
FROM trends t
JOIN trend_insights i ON i.trend_id = t.id
WHERE t.last_seen_at > now() - interval '24 hours'
ORDER BY t.velocity_per_hour DESC NULLS LAST
LIMIT 10
```

**Open high-priority recommendations**

```sql
SELECT id, title, type, trend_name, created_at
FROM recommendations
WHERE status = 'new' AND priority = 'high'
ORDER BY created_at DESC
LIMIT 20
```

## Presenting the result

- Lead with the answer, then the rows that support it.
- Say how many rows were returned and whether the result was truncated.
- Do not paste a large table unless the user asked for the raw data.
- If a table is plan-gated, the query fails with `plan_required`. Say which
  plan feature is missing; do not rewrite the query as a workaround.
- If a query is rejected, read the error code (`unknown_table`,
  `function_not_allowed`, `not_select`, `timeout`, `plan_required`) and correct
  the query once. Do not retry the same query.
