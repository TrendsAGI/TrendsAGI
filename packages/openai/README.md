# `@trendsagi/openai`

OpenAI function-calling tools for [TrendsAGI](https://trendsagi.com). The package returns plain JSON Schema tool definitions plus a dispatcher, so it works with the Responses API, Chat Completions and any OpenAI-compatible client.

```bash
npm install @trendsagi/openai @trendsagi/core openai
```

The OpenAI SDK is an optional peer dependency. The package never imports it at runtime.

## Tools

- `trendsagi_list_trends`
- `trendsagi_get_trend`
- `trendsagi_get_insights`
- `trendsagi_get_trend_dossier`
- `trendsagi_list_web_trends`
- `trendsagi_get_search_demand`
- `trendsagi_get_brand_momentum`
- `trendsagi_get_trend_creators`
- `trendsagi_ask_trend`
- `trendsagi_get_social_evidence`
- `trendsagi_get_social_evidence_credits`
- `trendsagi_list_recommendations`
- `trendsagi_preview_ads`

`trendsagi_preview_ads` only previews targeting changes. It never applies them.

## Responses API

```ts
import OpenAI from "openai";
import { TrendsAGI } from "@trendsagi/core";
import { createOpenAITools, runTrendsAGITool } from "@trendsagi/openai";

const trendsagi = new TrendsAGI();
const openai = new OpenAI();

const response = await openai.responses.create({
  model: "gpt-5-mini",
  input: "Find a rising skincare trend and summarize the opportunity.",
  tools: createOpenAITools(trendsagi),
});

console.log(response.output_text);
```

## Executing tool calls

The model returns tool calls; your code runs them and sends the result back.

```ts
let response = await openai.responses.create({
  model: "gpt-5-mini",
  input: "Find a rising skincare trend and summarize the opportunity.",
  tools: createOpenAITools(trendsagi),
});

while (true) {
  const calls = response.output.filter((item) => item.type === "function_call");
  if (calls.length === 0) break;

  const results = await Promise.all(
    calls.map(async (call) => ({
      type: "function_call_output" as const,
      call_id: call.call_id,
      output: JSON.stringify(
        await runTrendsAGITool(trendsagi, call.name, call.arguments),
      ),
    })),
  );

  response = await openai.responses.create({
    model: "gpt-5-mini",
    previous_response_id: response.id,
    input: results,
    tools: createOpenAITools(trendsagi),
  });
}

console.log(response.output_text);
```

## Chat Completions

```ts
const tools = createOpenAITools(trendsagi, { format: "chat" });

const completion = await openai.chat.completions.create({
  model: "gpt-4o-mini",
  messages: [{ role: "user", content: "What is rising in Technology?" }],
  tools,
});
```

## Arguments and errors

`runTrendsAGITool(client, name, args)` accepts either a JSON string (as returned by OpenAI) or an object. It validates the tool name, parses arguments and throws `TrendsAGIToolError` with `code: "UNKNOWN_TOOL" | "INVALID_ARGUMENTS"` on bad input.

All results are JSON-serializable.

## License

MIT © TrendsAGI. This is an official TrendsAGI package, not an OpenAI product. It is not affiliated with, endorsed by or sponsored by OpenAI. OpenAI and ChatGPT are trademarks of OpenAI.
