import { ChatOpenAI } from "@langchain/openai";
import { TrendsAGI } from "@trendsagi/core";
import { createTrendsAGITools } from "@trendsagi/langchain";

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
const tools = createTrendsAGITools(trendsagi);

if (!process.env.OPENAI_API_KEY) {
  console.log("No OPENAI_API_KEY set: printing the tools and invoking one against the mock.\n");
  console.log(tools.map((tool) => `- ${tool.name}`).join("\n"));
  const result = await tools[0].invoke({ category: "Technology", limit: 3 });
  console.log("\n" + JSON.stringify(result, null, 2));
  process.exit(0);
}

const model = new ChatOpenAI({
  model: process.env.OPENAI_MODEL ?? "gpt-4o-mini",
}).bindTools(tools);

const result = await model.invoke("Find a rising skincare trend and suggest a campaign angle.");
console.log(result.content);
