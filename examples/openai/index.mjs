import OpenAI from "openai";
import { TrendsAGI } from "@trendsagi/core";
import { createOpenAITools, runTrendsAGITool } from "@trendsagi/openai";

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
const tools = createOpenAITools(trendsagi, { format: "responses" });

if (!process.env.OPENAI_API_KEY) {
  console.log("No OPENAI_API_KEY set: printing the tools and running one against the mock.\n");
  console.log(tools.map((tool) => `- ${tool.name}`).join("\n"));
  const result = await runTrendsAGITool(trendsagi, "trendsagi_list_trends", {
    category: "Technology",
    limit: 3,
  });
  console.log("\n" + JSON.stringify(result, null, 2));
  process.exit(0);
}

const openai = new OpenAI();
const prompt = "Find a rising skincare trend and summarize the opportunity.";
let response = await openai.responses.create({
  model: process.env.OPENAI_MODEL ?? "gpt-5-mini",
  input: prompt,
  tools,
});

while (true) {
  const calls = response.output.filter((item) => item.type === "function_call");
  if (calls.length === 0) break;

  const results = await Promise.all(
    calls.map(async (call) => ({
      type: "function_call_output",
      call_id: call.call_id,
      output: JSON.stringify(await runTrendsAGITool(trendsagi, call.name, call.arguments)),
    })),
  );

  response = await openai.responses.create({
    model: process.env.OPENAI_MODEL ?? "gpt-5-mini",
    previous_response_id: response.id,
    input: results,
    tools,
  });
}

console.log(response.output_text);
