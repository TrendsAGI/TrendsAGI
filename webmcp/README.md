# TrendsAGI for WebMCP (browser agents)

[WebMCP](https://webmachinelearning.github.io/webmcp/) lets a web page register
tools with the browser, which offers them to the AI agent built into it. It is
in origin trials in Chrome (from 149) and Edge (from 150), supported in ChatGPT
desktop, and experimental in Brave's Leo. To try it on any recent Chrome, turn
on `chrome://flags/#enable-webmcp-testing`.

## Use TrendsAGI's own site (no setup)

- **app.trendsagi.com:** while you are signed in, the app registers TrendsAGI's
  read-only tools (`list_trends`, `get_trend_analytics`, `get_trend_ai_insights`,
  `list_recommendations`, `execute_sql` and the rest), plus `open_app_page`. They
  run with your session: no connector or API key, and calls count as app use,
  not API usage.
- **trendsagi.com:** every visitor's agent gets public tools: docs search, trend
  reports, plans, assistant setup steps and the free calculators.

Details and FAQ: <https://trendsagi.com/webmcp>

## Add TrendsAGI tools to your own site

Your page registers the tools; your server keeps the API key and runs them.

1. Serve the tools from your backend. With the Python SDK (0.16.0+),
   `TrendsAGITools.webmcp()` lists them and `tools.call()` runs one; see
   [`server.py`](server.py) for a FastAPI version.
2. In your page, register them:

   ```js
   import { registerTrendsAGITools } from "./trendsagi-webmcp.js";

   const unregister = await registerTrendsAGITools({ endpoint: "/trendsagi/tools" });
   ```

   [`trendsagi-webmcp.js`](trendsagi-webmcp.js) has no dependencies and does
   nothing in browsers without WebMCP.

Not using Python? The same tools are on the REST API:

```bash
curl https://api.trendsagi.com/api/agent/tools          # public tool list, WebMCP-shaped
curl -X POST https://api.trendsagi.com/api/agent/tools/list_trends \
  -H "Authorization: Bearer $TRENDSAGI_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"category": "Technology", "limit": 5}'
```

## Security

- Never put a TrendsAGI API key in page code; the browser and its agent can read it.
- Check your own user's sign-in before forwarding a call, or anyone can spend your quota.
- Tools are read-only (`readOnlyHint: true`) unless you opt in to writes. Tools
  whose results quote social posts or generated insights are marked
  `untrustedContentHint: true`, so the agent treats that text as data.
