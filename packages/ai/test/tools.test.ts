import { describe, expect, it } from "vitest";
import type { TrendsAGI } from "@trendsagi/core";
import { createTrendsAGITools } from "../src/index.js";

function stubClient() {
  const calls: Array<{ method: string; args: unknown[] }> = [];
  const record = (method: string) => async (...args: unknown[]) => {
    calls.push({ method, args });
    return { method, args };
  };
  const client = {
    trends: { list: record("trends.list"), get: record("trends.get") },
    insights: { get: record("insights.get") },
    recommendations: { list: record("recommendations.list") },
    ads: { preview: record("ads.preview") },
  } as unknown as TrendsAGI;
  return { client, calls };
}

type ExecutableTool = { execute?: (input: any, options: any) => Promise<any> };

describe("createTrendsAGITools (Vercel AI SDK)", () => {
  it("exposes the four AI SDK tools with input schemas", () => {
    const { client } = stubClient();
    const tools = createTrendsAGITools(client);
    expect(Object.keys(tools).sort()).toEqual([
      "get_trend_insights",
      "list_recommendations",
      "list_trends",
      "preview_ads",
    ]);
    for (const tool of Object.values(tools)) {
      expect(tool).toHaveProperty("inputSchema");
      expect(tool).toHaveProperty("description");
    }
  });

  it("executes list_trends", async () => {
    const { client, calls } = stubClient();
    const tools = createTrendsAGITools(client) as unknown as Record<string, ExecutableTool>;
    await tools.list_trends.execute?.({ category: "Technology", limit: 5 }, {});
    expect(calls[0]).toMatchObject({
      method: "trends.list",
      args: [{ category: "Technology", limit: 5 }],
    });
  });

  it("executes insights and recommendations", async () => {
    const { client, calls } = stubClient();
    const tools = createTrendsAGITools(client) as unknown as Record<string, ExecutableTool>;
    await tools.get_trend_insights.execute?.({ trend_id: 8 }, {});
    await tools.list_recommendations.execute?.({ priority: "critical" }, {});
    expect(calls.map((call) => call.method)).toEqual(["insights.get", "recommendations.list"]);
  });

  it("executes ads previews without applying them", async () => {
    const { client, calls } = stubClient();
    const tools = createTrendsAGITools(client) as unknown as Record<string, ExecutableTool>;
    await tools.preview_ads.execute?.(
      { platform: "google_ads", trend_id: 2, apply_level: "campaign" },
      {},
    );
    expect(calls[0].method).toBe("ads.preview");
    expect(calls[0].args[0]).toBe("google_ads");
    expect(calls[0].args[1]).toMatchObject({ trend_id: 2, apply_level: "campaign" });
  });

  it("validates input schemas with zod", async () => {
    const { client } = stubClient();
    const tools = createTrendsAGITools(client) as unknown as Record<string, any>;
    const parsed = tools.preview_ads.inputSchema.safeParse({
      platform: "google_ads",
      trend_id: -1,
    });
    expect(parsed.success).toBe(false);
  });
});
