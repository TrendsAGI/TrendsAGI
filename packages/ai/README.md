# `@trendsagi/ai`

Vercel AI SDK tools for [TrendsAGI](https://trendsagi.com). The package exposes four `tool()` objects with `inputSchema` zod definitions, ready for `generateText`, `streamText` and agent loops.

```bash
npm install @trendsagi/ai @trendsagi/core ai @ai-sdk/openai zod
```

`ai` and `zod` are peer dependencies.

## Tools

- `list_trends`
- `get_trend_insights`
- `list_recommendations`
- `preview_ads`

`preview_ads` only previews targeting changes. It never applies them.

## Example

```ts
import { generateText } from "ai";
import { openai } from "@ai-sdk/openai";
import { TrendsAGI } from "@trendsagi/core";
import { createTrendsAGITools } from "@trendsagi/ai";

const trendsagi = new TrendsAGI();
const { text } = await generateText({
  model: openai("gpt-5-mini"),
  tools: createTrendsAGITools(trendsagi),
  prompt: "Find a rising skincare trend and suggest a campaign angle.",
});

console.log(text);
```

## Direct invocation

```ts
const tools = createTrendsAGITools(trendsagi);
const result = await tools.list_trends.execute?.({ category: "Beauty", limit: 5 }, {});
```

## License

MIT © TrendsAGI. This is an official TrendsAGI package, not a Vercel product. It is not affiliated with, endorsed by or sponsored by Vercel. Vercel and the AI SDK are trademarks of Vercel.
