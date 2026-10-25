import { generateText } from "ai";
import { openai } from "@ai-sdk/openai";
import { TrendsAGI } from "@trendsagi/core";
import { createTrendsAGITools } from "@trendsagi/ai";

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
  console.log("No OPENAI_API_KEY set: printing the tools and executing one against the mock.\n");
  console.log(Object.keys(tools).map((name) => `- ${name}`).join("\n"));
  const result = await tools.list_trends.execute?.({ category: "Technology", limit: 3 }, {});
  console.log("\n" + JSON.stringify(result, null, 2));
  process.exit(0);
}

const { text } = await generateText({
  model: openai(process.env.OPENAI_MODEL ?? "gpt-5-mini"),
  tools,
  prompt: "Find a rising skincare trend and suggest a campaign angle.",
});

console.log(text);
