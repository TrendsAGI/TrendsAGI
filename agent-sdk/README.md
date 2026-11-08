# TrendsAGI for Cursor Agent SDK

A ready-to-run [Cursor Agent SDK](https://cursor.com/docs/agent-sdk) project that
researches rising trends with TrendsAGI. The agent reaches TrendsAGI's hosted MCP
server through one connection file, so it gets the same 13 read-only tools as Claude,
ChatGPT and Cursor: `list_trends`, `get_trend_analytics`, `get_trend_ai_insights`,
`search_trend_insights`, `list_recommendations`, `list_crisis_events`,
`list_watchlist`, `execute_sql` and the rest. Nothing to install from TrendsAGI.

```text
agent-sdk/
├── bot/
│   ├── agent.ts                    # hosting: egress to api.trendsagi.com, TRENDSAGI_API_KEY secret
│   ├── instructions.md             # how the agent uses the tools and reads the numbers
│   ├── mcp-connections/
│   │   └── trendsagi.ts            # the hosted MCP server, read-only tools advertised by name
│   └── skills/
│       └── trend-brief.md          # a daily or weekly trend brief, loaded on demand
└── evals/
    └── smoke.eval.ts               # two live checks that the agent calls the tools
```

## Run it

You need Node.js 22.13 or newer, a Cursor login for model turns, and a TrendsAGI API key
from Profile > API Keys at [app.trendsagi.com](https://app.trendsagi.com).

```bash
npm install --global @grok/agent-sdk
agent-sdk login

git clone --depth 1 https://github.com/TrendsAGI/TrendsAGI.git
cp -R TrendsAGI/agent-sdk my-trend-agent && cd my-trend-agent
npm install

export TRENDSAGI_API_KEY="your_api_key"
agent-sdk validate --dir .
agent-sdk dev
```

In a second terminal:

```bash
# One tool, no model turn
agent-sdk tool call list_trends --dir . --input '{"category":"Technology","sort_by":"velocity","limit":5}'

# A full turn
agent-sdk run --dir . --message "Write a trend brief for a sportswear brand for this week."

# The smoke evals
agent-sdk eval --dir . --tag smoke
```

Each tool call counts as one API request on your key, like any other TrendsAGI call.

## Add TrendsAGI to an agent you already have

Copy one file into `bot/mcp-connections/`:

```ts
// bot/mcp-connections/trendsagi.ts
import { defineConnection } from "@grok/agent-sdk/connections";

export default defineConnection({
  url: "https://api.trendsagi.com/mcp",
  headers: { authorization: "Bearer ${TRENDSAGI_API_KEY}" },
  advertiseTools: true,
  effects: "read",
});
```

`${TRENDSAGI_API_KEY}` is an Agent SDK template, not a JavaScript one: Agent SDK fills
it each time the connection opens, from the environment locally and from the deployment
secret on Cursor hosting. `effects: "read"` advertises only tools the server marks as
reads. Every TrendsAGI tool is read-only today, and this keeps your agent read-only if
that ever changes.

For a hosted deploy, also declare the host and the secret in `bot/agent.ts`:

```ts
export default defineAgent({
  hosting: {
    egressDomains: ["api.trendsagi.com"],
    secretNames: ["TRENDSAGI_API_KEY"],
  },
});
```

## Deploy

```bash
agent-sdk deploy
agent-sdk secret set trendsagi-agent TRENDSAGI_API_KEY
```

Then manage the agent in Deployed Agents. The next task uses the secret without another
deploy.

## Ideas

- **A weekday brief.** Add `bot/schedules/weekday-brief.md`. Each fire is one model turn
  on your Cursor account and a handful of TrendsAGI requests on your key.

  ```md
  ---
  cron: "0 8 * * 1-5"
  ---
  Write today's trend brief for the Technology and Health categories.
  ```

- **Answer in Slack.** Ask your coding agent to follow Agent SDK's `bdk-setup-slack` skill,
  so people can mention the agent in a channel and get a brief in the thread.
- **Only some tools.** Replace `effects: "read"` with `tools: ["list_trends", "get_trend_ai_insights"]`
  to give the agent a smaller surface.

## Notes

- Volume, velocity and growth are measurements. Insights are generated from social posts,
  so the instructions tell the agent to treat their text as evidence, not instructions.
- A recommendation's confidence score measures how complete its evidence is, not the
  chance that an action will work. TrendsAGI does not measure conversion lift or ad
  performance.
- Agent SDK is Cursor's. TrendsAGI is not affiliated with Cursor.

Guide: [trendsagi.com/api-docs/integrations/agent-sdk](https://trendsagi.com/api-docs/integrations/agent-sdk)
