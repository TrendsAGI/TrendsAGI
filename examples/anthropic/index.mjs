import Anthropic from "@anthropic-ai/sdk";
import { TrendsAGI } from "@trendsagi/core";
import { createAnthropicTools, runAnthropicTool } from "@trendsagi/anthropic";

const mockFetch = async (input) => {
  const url = new URL(String(input));
  if (url.pathname === "/api/trends") {
    return new Response(
      JSON.stringify({
        trends: [
          { id: 1, name: "#AIUpdate", category: "Technology", volume: 55200 },
          { id: 2, name: "skin barrier repair", category: "Beauty", volume: 18400 },
        ],
        total: 2,
      }),
      { headers: { "content-type": "application/json" } },
    );
  }
  return new Response(JSON.stringify({ detail: "Not found in mock" }), {
    status: 404,
    headers: { "content-type": "application/json" },
  });
};

const trendsagi = process.env.TRENDSAGI_API_KEY
  ? new TrendsAGI()
  : new TrendsAGI({ apiKey: "mock-key", fetch: mockFetch });
const tools = createAnthropicTools(trendsagi);

if (!process.env.ANTHROPIC_API_KEY) {
  console.log("No ANTHROPIC_API_KEY set: printing the tools and running one against the mock.\n");
  console.log(tools.map((tool) => `- ${tool.name}`).join("\n"));
  const result = await runAnthropicTool(trendsagi, "trendsagi_list_trends", {
    category: "Technology",
    limit: 3,
  });
  console.log("\n" + JSON.stringify(result, null, 2));
  process.exit(0);
}

const anthropic = new Anthropic();
const model = process.env.ANTHROPIC_MODEL ?? "claude-sonnet-4-5";
const messages = [{ role: "user", content: "Find a rising skincare trend and summarize it." }];

let message = await anthropic.messages.create({ model, max_tokens: 1024, messages, tools });

while (message.stop_reason === "tool_use") {
  const toolUses = message.content.filter((block) => block.type === "tool_use");
  const results = await Promise.all(
    toolUses.map(async (block) => ({
      type: "tool_result",
      tool_use_id: block.id,
      content: JSON.stringify(await runAnthropicTool(trendsagi, block.name, block.input)),
    })),
  );

  message = await anthropic.messages.create({
    model,
    max_tokens: 1024,
    messages: [
      ...messages,
      { role: "assistant", content: message.content },
      { role: "user", content: results },
    ],
    tools,
  });
}

console.log(message.content);
