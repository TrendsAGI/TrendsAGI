# Paid-media decision playbook

Use this when the user asks what to target, when to move budget, which audience
to reach, or which creative angle to test. The goal is a decision backed by
measured demand, not a list of trending words.

## 1. Classify the signal

For each candidate trend, collect:

- **Volume** - how large the audience is right now.
- **Velocity** - change in volume per hour; the fastest acceleration is usually
  the best timing signal.
- **Growth** - percent change from the previous measurement.
- **Trajectory** - `get_trend_analytics` over `24h` and `7d`.

Then classify:

| Pattern | 24h | 7d | Meaning for paid media |
| --- | --- | --- | --- |
| Rising | Up | Up | Demand is building. Best window to test or scale, if brand-safe. |
| Peaking | Up | Flat | Attention is high but acceleration is slowing. Defend, do not chase a higher CPC. |
| Fading | Down | Down | The audience is moving on. Hold or pull budget; do not launch a new campaign on it. |
| Spiky | Sharp up | One-off | Verify with a second reading and check crisis events before acting. |
| Thin | Low volume | Any | Do not build a campaign on one weak signal; widen the search or period. |

Never call a trend rising from a single datapoint. `get_trend_analytics` is the
tool that turns a snapshot into a trajectory.

## 2. Choose the audience

Use `get_trend_ai_insights` when the account's plan includes it. Mine:

- `audience` or `audience_injection` for demographics, interest keywords and
  negative keywords.
- `key_themes` for the language the audience uses.
- `sentiment` for whether the angle should be positive, cautionary or neutral.
- `ad_platform_targeting` for platform-specific suggestions.

If the insight is missing, say so and fall back to the trend's category,
description and name. Do not invent demographics.

## 3. Choose the angle

Turn the signal into one or two testable angles:

- **Momentum angle** - "X is accelerating; here is why it matters now."
- **Audience angle** - "People already interested in Y are driving this."
- **Contrarian angle** - only when sentiment is mixed or negative and the brand
  can credibly take that position.
- **Utility angle** - a how-to, comparison or savings angle for high-intent
  topics.

Keep the angle tied to a measured theme. A creative that merely repeats the
trend name is not a strategy.

## 4. Check brand safety

Before recommending more spend on a brand, competitor or sensitive topic:

1. `list_crisis_events` with `status: "active"` and a suitable `time_range`.
2. If a crisis event exists, report its severity and summary before any budget
   advice.
3. If the plan does not include crisis monitoring, say that the check was not
   available rather than implying the topic is safe.

## 5. Check the account's own guidance

`list_recommendations` is the account's prior analysis. Prefer an existing
high-priority recommendation over inventing a new plan, and cite its decision
brief. If the user asks what to do next, start there.

## 6. Write the answer

Use this structure:

```
Signal:        <topic> (trend id <id>), <volume> volume, <velocity>/h,
               <growth>% growth, <period>, category <category>.
Trajectory:    Rising / peaking / fading over 24h and 7d, with the series.
Audience:      Who is reached, sentiment, themes, and any plan gap.
Angle:         One or two specific creative or keyword angles.
Evidence:      Tools used; recommendation confidence = evidence completeness,
               not probability of success.
Caveats:       Plan-gated data, thin volume, stale insight, or crisis event.
Next action:   Test / scale / hold / pull, with the smallest useful next step.
```

## Worked examples

**"What should we target in Technology this week?"**

1. `list_trends` with `category: "Technology"`, `sort_by: "velocity"`,
   `period: "7d"`, `limit: 10`.
2. Pick the top two with meaningful volume; `get_trend_analytics` for each over
   `7d`.
3. `get_trend_ai_insights` for the one that is still rising.
4. Answer with the signal, trajectory, audience, one angle, evidence and
   caveats.

**"Is this brand trend still worth spending on?"**

1. `list_trends` with `search: "<brand>"`, `period: "30d"`.
2. `get_trend_analytics` over `24h` and `7d`.
3. `list_crisis_events` before recommending an increase.
4. If fading, recommend holding or pulling spend; do not soften the finding.

**"Which categories are growing fastest?"**

1. `read_data_schema`.
2. `execute_sql` with the category-growth query from `references/sql.md`.
3. Rank by average growth, but flag categories with thin trend counts before
   calling one a winner.

## Guardrails

- TrendsAGI measures trend volume, velocity and growth. It does not measure
  impressions, clicks, conversions, ROAS or revenue lift.
- Never turn a trend measurement into a forecast of ad performance.
- Confidence scores describe evidence completeness, not the chance an action
  succeeds.
- Recommendations are suggestions. The hosted connection cannot change a
  campaign, a budget, a bid or an audience.
