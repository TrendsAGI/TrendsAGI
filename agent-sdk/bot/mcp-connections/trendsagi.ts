import { defineConnection } from "@grok/agent-sdk/connections";

// TrendsAGI's hosted MCP server accepts an API key as a Bearer token. Agent SDK
// fills ${TRENDSAGI_API_KEY} each time the connection opens, from the
// environment locally and from the deployment secret on Cursor hosting.
export default defineConnection({
  url: "https://api.trendsagi.com/mcp",
  headers: { authorization: "Bearer ${TRENDSAGI_API_KEY}" },
  // Expose the server's tools by name (list_trends, get_trend_ai_insights, ...).
  advertiseTools: true,
  // Every TrendsAGI tool is read-only today; this keeps it that way for the agent.
  effects: "read",
});
