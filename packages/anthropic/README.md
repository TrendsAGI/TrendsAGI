# `@trendsagi/anthropic`

Anthropic tool definitions and a dispatcher for [TrendsAGI](https://trendsagi.com). The package returns Claude `tool` objects with `input_schema`, plus a runner for `tool_use` blocks.

```bash
npm install @trendsagi/anthropic @trendsagi/core @anthropic-ai/sdk
```

The Anthropic SDK is an optional peer dependency. The package never imports it at runtime.

## Tools

- `trendsagi_list_trends`
- `trendsagi_get_trend`
- `trendsagi_get_insights`
- `trendsagi_list_recommendations`
- `trendsagi_preview_ads`

`trendsagi_preview_ads` only previews targeting changes. It never applies them.

## Example

```ts
import Anthropic from "@anthropic-ai/sdk";
import { TrendsAGI } from "@trendsagi/core";
import { createAnthropicTools, runAnthropicTool } from "@trendsagi/anthropic";

const anthropic = new Anthropic();
const trendsagi = new TrendsAGI();
const tools = createAnthropicTools(trendsagi);

let message = await anthropic.messages.create({
  model: "claude-sonnet-4-5",
  max_tokens: 1024,
  messages: [{ role: "user", content: "Find a rising skincare trend." }],
  tools,
});

while (message.stop_reason === "tool_use") {
  const toolUses = message.content.filter((block) => block.type === "tool_use");
  const results = await Promise.all(
    toolUses.map(async (block) => ({
      type: "tool_result" as const,
      tool_use_id: block.id,
      content: JSON.stringify(await runAnthropicTool(trendsagi, block.name, block.input)),
    })),
  );

  message = await anthropic.messages.create({
    model: "claude-sonnet-4-5",
    max_tokens: 1024,
    messages: [
      { role: "user", content: "Find a rising skincare trend." },
      { role: "assistant", content: message.content },
      { role: "user", content: results },
    ],
    tools,
  });
}

console.log(message.content);
```

## Definitions only

```ts
const tools = createAnthropicTools(); // no client needed to describe the tools
```

## License

MIT © TrendsAGI. This is an official TrendsAGI package, not an Anthropic product. It is not affiliated with, endorsed by or sponsored by Anthropic. Claude is a trademark of Anthropic.
