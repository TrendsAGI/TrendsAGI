# `@trendsagi/langchain`

LangChain tools for [TrendsAGI](https://trendsagi.com). Every tool returns JSON-serializable data and uses a zod schema, so a LangChain agent can call live trend data deterministically.

```bash
npm install @trendsagi/langchain @trendsagi/core @langchain/openai zod
```

`@langchain/core` and `zod` are peer dependencies.

## Tools

- `list_trends`
- `get_trend_insights`
- `list_recommendations`
- `preview_ads`

`preview_ads` only previews targeting changes. It never applies them.

## Example

```ts
import { ChatOpenAI } from "@langchain/openai";
import { TrendsAGI } from "@trendsagi/core";
import { createTrendsAGITools } from "@trendsagi/langchain";

const trendsagi = new TrendsAGI();
const model = new ChatOpenAI({ model: "gpt-4o-mini" }).bindTools(
  createTrendsAGITools(trendsagi),
);

const result = await model.invoke("Find a rising skincare trend.");
console.log(result.content);
```

## Direct invocation

```ts
const [listTrends] = createTrendsAGITools(trendsagi);
const result = await listTrends.invoke({ category: "Technology", limit: 5 });
```

## License

MIT © TrendsAGI. This is an official TrendsAGI package, not a LangChain product. It is not affiliated with, endorsed by or sponsored by LangChain.
