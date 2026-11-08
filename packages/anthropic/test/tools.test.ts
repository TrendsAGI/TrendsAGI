import { describe, expect, it } from "vitest";
import type { TrendsAGI } from "@trendsagi/core";
import {
  createAnthropicTools,
  runAnthropicTool,
  TRENDSAGI_ANTHROPIC_TOOL_NAMES,
} from "../src/index.js";

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

describe("createAnthropicTools", () => {
  it("returns Anthropic tool definitions", () => {
    const tools = createAnthropicTools();
    expect(tools.map((tool) => tool.name)).toEqual([...TRENDSAGI_ANTHROPIC_TOOL_NAMES]);
    for (const tool of tools) {
      expect(tool.input_schema.type).toBe("object");
      expect(typeof tool.description).toBe("string");
    }
  });

  it("marks required inputs in the schema", () => {
    const tools = createAnthropicTools();
    const preview = tools.find((tool) => tool.name === "trendsagi_preview_ads");
    expect(preview?.input_schema.required).toEqual(["platform", "trend_id"]);
    const insights = tools.find((tool) => tool.name === "trendsagi_get_insights");
    expect(insights?.input_schema.required).toEqual(["trend_id"]);
  });

  it("accepts a client for API symmetry", () => {
    const { client } = stubClient();
    expect(createAnthropicTools(client)).toHaveLength(13);
  });
});

describe("runAnthropicTool", () => {
  it("dispatches list_trends", async () => {
    const { client, calls } = stubClient();
    await runAnthropicTool(client, "trendsagi_list_trends", {
      category: "Travel",
      limit: 4,
    });
    expect(calls[0]).toMatchObject({
      method: "trends.list",
      args: [{ category: "Travel", limit: 4 }],
    });
  });

  it("dispatches get_trend and get_insights", async () => {
    const { client, calls } = stubClient();
    await runAnthropicTool(client, "trendsagi_get_trend", { trend_id: 11 });
    await runAnthropicTool(client, "trendsagi_get_insights", { trend_id: 11 });
    expect(calls.map((call) => call.method)).toEqual(["trends.get", "insights.get"]);
  });

  it("dispatches ads previews with the platform separated", async () => {
    const { client, calls } = stubClient();
    await runAnthropicTool(client, "trendsagi_preview_ads", {
      platform: "tiktok_ads",
      trend_id: 5,
      strict_safety: false,
    });
    expect(calls[0].args[0]).toBe("tiktok_ads");
    expect(calls[0].args[1]).toMatchObject({ trend_id: 5, strict_safety: false });
  });

  it("dispatches dossier, discovery and social evidence tools", async () => {
    const { client, calls } = stubClient();
    await runAnthropicTool(client, "trendsagi_get_trend_dossier", { trend_id: 7 });
    await runAnthropicTool(client, "trendsagi_list_web_trends", { limit: 5 });
    await runAnthropicTool(client, "trendsagi_get_search_demand", { trend_id: 7, geo: "UK" });
    await runAnthropicTool(client, "trendsagi_get_brand_momentum", { trend_id: 7, window: "30d" });
    await runAnthropicTool(client, "trendsagi_get_trend_creators", { trend_id: 7 });
    await runAnthropicTool(client, "trendsagi_ask_trend", { trend_id: 7, question: "What now?" });
    await runAnthropicTool(client, "trendsagi_get_social_evidence", { trend_id: 7 });
    await runAnthropicTool(client, "trendsagi_get_social_evidence_credits", {});
    expect(calls.map((call) => call.method)).toEqual([
      "trends.dossier",
      "trends.discoveries",
      "trends.searchDemand",
      "trends.brandMomentum",
      "trends.creators",
      "trends.ask",
      "trends.socialEvidence",
      "credits.socialEvidence",
    ]);
  });

  it("rejects unknown tools and missing required inputs", async () => {
    const { client } = stubClient();
    await expect(runAnthropicTool(client, "nope", {})).rejects.toMatchObject({
      code: "UNKNOWN_TOOL",
    });
    await expect(runAnthropicTool(client, "trendsagi_preview_ads", {})).rejects.toMatchObject({
      code: "INVALID_ARGUMENTS",
    });
  });
});
