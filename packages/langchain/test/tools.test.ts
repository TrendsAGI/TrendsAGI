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
    trends: {
      list: record("trends.list"),
      get: record("trends.get"),
      dossier: record("trends.dossier"),
      discoveries: record("trends.discoveries"),
      searchDemand: record("trends.searchDemand"),
      brandMomentum: record("trends.brandMomentum"),
      creators: record("trends.creators"),
      ask: record("trends.ask"),
      socialEvidence: record("trends.socialEvidence"),
    },
    insights: { get: record("insights.get") },
    recommendations: { list: record("recommendations.list") },
    ads: { preview: record("ads.preview") },
    credits: { socialEvidence: record("credits.socialEvidence") },
  } as unknown as TrendsAGI;
  return { client, calls };
}

describe("createTrendsAGITools", () => {
  it("exposes the LangChain tools", () => {
    const { client } = stubClient();
    const tools = createTrendsAGITools(client);
    expect(tools.map((tool) => tool.name)).toEqual([
      "list_trends",
      "get_trend_insights",
      "list_recommendations",
      "get_trend_dossier",
      "list_web_trends",
      "get_search_demand",
      "get_brand_momentum",
      "get_trend_creators",
      "ask_trend",
      "get_social_evidence",
      "get_social_evidence_credits",
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
    const tools = createTrendsAGITools(client);
    const getInsights = tools.find((tool) => tool.name === "get_trend_insights")!;
    const listRecommendations = tools.find((tool) => tool.name === "list_recommendations")!;
    await getInsights.invoke({ trend_id: 3 });
    await listRecommendations.invoke({ priority: "high", match_user_interests: true });
    expect(calls.map((call) => call.method)).toEqual(["insights.get", "recommendations.list"]);
  });

  it("invokes ads previews with the platform separated from the body", async () => {
    const { client, calls } = stubClient();
    const previewAds = createTrendsAGITools(client).find((tool) => tool.name === "preview_ads")!;
    await previewAds.invoke({
      platform: "meta_ads",
      trend_id: 4,
      apply_level: "ad_group",
      strict_safety: true,
    });
    expect(calls[0].args[0]).toBe("meta_ads");
    expect(calls[0].args[1]).toMatchObject({ trend_id: 4, apply_level: "ad_group", strict_safety: true });
  });

  it("invokes dossier and social evidence tools", async () => {
    const { client, calls } = stubClient();
    const tools = createTrendsAGITools(client);
    await tools.find((tool) => tool.name === "get_trend_dossier")!.invoke({ trend_id: 7 });
    await tools.find((tool) => tool.name === "get_social_evidence_credits")!.invoke({});
    expect(calls.map((call) => call.method)).toEqual(["trends.dossier", "credits.socialEvidence"]);
  });

  it("validates arguments with zod", async () => {
    const { client } = stubClient();
    const previewAds = createTrendsAGITools(client).find((tool) => tool.name === "preview_ads")!;
    await expect(previewAds.invoke({ platform: "not_a_platform", trend_id: 4 })).rejects.toThrow();
  });
});
