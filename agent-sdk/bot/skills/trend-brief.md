---
description: Use when asked for a trend brief, a weekly or daily trend summary, or which rising topics a team should act on.
---

# Trend brief

1. Call `list_trends` with `sort_by: "velocity"` and the requested category or
   phrase. Use `period: "7d"` for a weekly brief and `"24h"` otherwise, and
   keep `limit` at 10 or fewer.
2. Pick the three trends with the strongest velocity that fit the request.
   For each one, call `get_trend_analytics` and `get_trend_ai_insights`.
3. Call `list_recommendations` with `match_user_interests: true` and include
   any recommendation that names one of the three trends.
4. Call `list_crisis_events` with `status: "active"` and mention any event
   that touches the same topics.
5. Write the brief:
   - One line per trend: name, id, volume, velocity, growth and the period.
   - The audience and the strongest marketing angle from its insight.
   - A **Risks** line for crisis events or negative sentiment.
   - **First action**: the one thing to do today, and which trend it uses.

Do not invent figures. If a tool returns an error or nothing, say so in the
brief instead of filling the gap.
