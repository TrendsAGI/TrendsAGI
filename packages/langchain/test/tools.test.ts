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

describe("createTrendsAGITools", () => {
  it("exposes the four LangChain tools", () => {
    const { client } = stubClient();
    const tools = createTrendsAGITools(client);
    expect(tools.map((tool) => tool.name)).toEqual([
      "list_trends",
      "get_trend_insights",
      "list_recommendations",
      "preview_ads",
    ]);
    expect(tools.every((tool) => typeof tool.description === "string")).toBe(true);
    expect(tools.every((tool) => tool.schema !== undefined)).toBe(true);
  });

  it("invokes list_trends against the core client", async () => {
    const { client, calls } = stubClient();
    const [listTrends] = createTrendsAGITools(client);
    await listTrends.invoke({ category: "Beauty", limit: 5, sort_by: "velocity" });
    expect(calls[0]).toMatchObject({
      method: "trends.list",
      args: [{ category: "Beauty", limit: 5, sort_by: "velocity" }],
    });
  });

  it("invokes insights and recommendations", async () => {
    const { client, calls } = stubClient();
    const [, getInsights, listRecommendations] = createTrendsAGITools(client);
    await getInsights.invoke({ trend_id: 3 });
    await listRecommendations.invoke({ priority: "high", match_user_interests: true });
    expect(calls.map((call) => call.method)).toEqual(["insights.get", "recommendations.list"]);
  });

  it("invokes ads previews with the platform separated from the body", async () => {
    const { client, calls } = stubClient();
    const [, , , previewAds] = createTrendsAGITools(client);
    await previewAds.invoke({
      platform: "meta_ads",
      trend_id: 4,
      apply_level: "ad_group",
      strict_safety: true,
    });
    expect(calls[0].args[0]).toBe("meta_ads");
    expect(calls[0].args[1]).toMatchObject({ trend_id: 4, apply_level: "ad_group", strict_safety: true });
  });

  it("validates arguments with zod", async () => {
    const { client } = stubClient();
    const [, , , previewAds] = createTrendsAGITools(client);
    await expect(previewAds.invoke({ platform: "not_a_platform", trend_id: 4 })).rejects.toThrow();
  });
});
