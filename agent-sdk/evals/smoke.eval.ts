import { defineEval, includes } from "@grok/agent-sdk/evals";

// Live smoke checks: they call TrendsAGI with TRENDSAGI_API_KEY and count as
// API requests on that key.
export default defineEval({
  tags: ["smoke"],
  cases: [
    {
      id: "rising-technology",
      description: "Answers from list_trends instead of guessing.",
      async test(t) {
        await t.send("What is rising fastest in Technology right now? Give me three trends.");
        t.succeeded();
        t.calledTool("list_trends");
      },
    },
    {
      id: "trend-brief",
      description: "A brief checks the trajectory and insight before recommending.",
      async test(t) {
        await t.send("Write a short trend brief for a sportswear brand for this week.");
        t.succeeded();
        t.calledTool("get_trend_analytics");
        t.calledTool("get_trend_ai_insights");
        t.check(t.reply, includes(/first action/i));
      },
    },
  ],
});
