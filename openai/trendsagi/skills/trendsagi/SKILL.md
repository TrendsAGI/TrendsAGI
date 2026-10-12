---
name: trendsagi
description: >-
  Use TrendsAGI's live trend data to help paid media and growth teams decide what
  to target and when: find topics accelerating in a market, check whether a trend
  is still rising before moving budget, pull audience, sentiment and marketing
  angles for ad copy, and review evidence-backed recommendations. Use whenever
  TrendsAGI, trending topics, trend velocity, audience or keyword targeting from
  trends, campaign timing, or ad angles based on what is trending come up.
---

# TrendsAGI

TrendsAGI measures what is trending across social platforms in real time
(volume, velocity, growth) and turns it into evidence-backed recommendations.
The `trendsagi` MCP server bundled with this plugin is hosted at
`https://api.trendsagi.com/mcp` and acts as the signed-in TrendsAGI user. Every
tool is read-only.

## Workflows

**What should we target now?**
1. `list_trends` with `sort_by: "velocity"`, plus a `category` (see
   `list_trend_categories`) or a `search` phrase for the brand, product or
   competitor.
2. For the top few, `get_trend_analytics` (`period: "7d"`) to confirm the
   trajectory is still rising rather than already peaking.
3. `get_trend_ai_insights` for audience, themes, sentiment and marketing angles.
4. Summarise as: topic, why it is moving, who it reaches, suggested angle, and
   how confident the evidence is.

**Should we scale or pull spend on X?**
1. Find the trend with `list_trends` (`search`) or `search_trend_insights`.
2. `get_trend_analytics` over `24h` and `7d`: rising, flat or fading.
3. `list_crisis_events` before recommending more spend on a brand or topic.

**What should we do next?**
1. `list_recommendations` (filter by `priority` or `recommendation_type`, e.g.
   `marketing_angle`).
2. Present each with its decision brief and evidence, highest priority first.

## Rules

- **Report measurements as measurements.** Volume, velocity and growth come from
  TrendsAGI. Do not invent numbers, and never present a projected conversion
  lift or ROAS as a TrendsAGI figure; TrendsAGI does not measure those.
- **Confidence is evidence completeness**, not the probability that an action
  will work. Say so when you quote it.
- **Mind the limits.** Calls count toward the account's API plan. Prefer small
  `limit` values, and if a tool reports a rate or daily limit, call
  `get_api_usage` and tell the user rather than retrying in a loop.
- **Plan-gated data.** A `403` with an upgrade hint means the account's plan does
  not include that data; tell the user instead of retrying.
- **Reconnect on 401.** It means the connection's key was revoked; the user can
  reconnect TrendsAGI from the plugin settings.
