import { describe, expect, it, vi } from "vitest";
import type { TrendsAGI } from "@trendsagi/core";
import {
  createOpenAITools,
  runTrendsAGITool,
  TRENDSAGI_OPENAI_TOOL_NAMES,
  TrendsAGIToolError,
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

describe("createOpenAITools", () => {
  it("returns the TrendsAGI tool names", () => {
    const { client } = stubClient();
    const tools = createOpenAITools(client);
    expect(tools.map((tool) => ("name" in tool ? tool.name : tool.function.name))).toEqual([
      ...TRENDSAGI_OPENAI_TOOL_NAMES,
    ]);
  });

  it("uses the flat Responses API shape by default", () => {
    const { client } = stubClient();
    const tool = createOpenAITools(client)[0] as Record<string, any>;
    expect(tool.type).toBe("function");
    expect(tool.name).toBe("trendsagi_list_trends");
    expect(tool.parameters.type).toBe("object");
    expect(tool.function).toBeUndefined();
  });

  it("uses the nested Chat Completions shape when requested", () => {
    const { client } = stubClient();
    const tool = createOpenAITools(client, { format: "chat" })[0] as Record<string, any>;
    expect(tool.type).toBe("function");
    expect(tool.function.name).toBe("trendsagi_list_trends");
    expect(tool.function.parameters.type).toBe("object");
    expect(tool.name).toBeUndefined();
  });

  it("uses JSON Schema for required fields and enums", () => {
    const { client } = stubClient();
    const tools = createOpenAITools(client) as Array<Record<string, any>>;
    const getInsights = tools.find((tool) => tool.name === "trendsagi_get_insights");
    expect(getInsights?.parameters.required).toEqual(["trend_id"]);
    const preview = tools.find((tool) => tool.name === "trendsagi_preview_ads");
    expect(preview?.parameters.required).toEqual(["platform", "trend_id"]);
    expect(preview?.parameters.properties.platform.enum).toContain("google_ads");
  });

  it("rejects an unknown format", () => {
    const { client } = stubClient();
    expect(() => createOpenAITools(client, { format: "xml" as never })).toThrowError(
      TrendsAGIToolError,
    );
  });
});

describe("runTrendsAGITool", () => {
  it("dispatches list_trends with mapped arguments", async () => {
    const { client, calls } = stubClient();
    await runTrendsAGITool(client, "trendsagi_list_trends", {
      category: "Technology",
      limit: 5,
      sort_by: "velocity",
    });
    expect(calls[0]).toEqual({
      method: "trends.list",
      args: [{ category: "Technology", search: undefined, limit: 5, sort_by: "velocity", period: undefined }],
    });
  });

  it("accepts arguments as a JSON string", async () => {
    const { client, calls } = stubClient();
    await runTrendsAGITool(client, "trendsagi_get_trend", '{"trend_id":42}');
    expect(calls[0]).toEqual({ method: "trends.get", args: [42] });
  });

  it("dispatches insights, recommendations and ads previews", async () => {
    const { client, calls } = stubClient();
    await runTrendsAGITool(client, "trendsagi_get_insights", { trend_id: 7 });
    await runTrendsAGITool(client, "trendsagi_list_recommendations", {
      priority: "high",
      match_user_interests: true,
    });
    await runTrendsAGITool(client, "trendsagi_preview_ads", {
      platform: "google_ads",
      trend_id: 9,
      apply_level: "ad_group",
      strict_safety: true,
    });
    expect(calls.map((call) => call.method)).toEqual([
      "insights.get",
      "recommendations.list",
      "ads.preview",
    ]);
    expect(calls[2].args).toEqual([
      "google_ads",
      { trend_id: 9, apply_level: "ad_group", strict_safety: true },
    ]);
  });

  it("dispatches dossier, discovery, deep dive and social evidence tools", async () => {
    const { client, calls } = stubClient();
    await runTrendsAGITool(client, "trendsagi_get_trend_dossier", { trend_id: 7 });
    await runTrendsAGITool(client, "trendsagi_list_web_trends", { limit: 5 });
    await runTrendsAGITool(client, "trendsagi_get_search_demand", { trend_id: 7, geo: "UK" });
    await runTrendsAGITool(client, "trendsagi_get_brand_momentum", { trend_id: 7, window: "30d" });
    await runTrendsAGITool(client, "trendsagi_get_trend_creators", { trend_id: 7 });
    await runTrendsAGITool(client, "trendsagi_ask_trend", { trend_id: 7, question: "What now?" });
    await runTrendsAGITool(client, "trendsagi_get_social_evidence", { trend_id: 7 });
    await runTrendsAGITool(client, "trendsagi_get_social_evidence_credits", {});
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
    expect(calls[1].args).toEqual([{ limit: 5 }]);
    expect(calls[2].args).toEqual([7, { geo: "UK" }]);
    expect(calls[5].args).toEqual([7, "What now?"]);
  });

  it("returns an availability marker when no insight exists", async () => {
    const client = {
      insights: { get: async () => null },
    } as unknown as TrendsAGI;
    await expect(runTrendsAGITool(client, "trendsagi_get_insights", { trend_id: 3 })).resolves.toEqual(
      { trend_id: 3, available: false },
    );
  });

  it("rejects unknown tool names", async () => {
    const { client } = stubClient();
    await expect(runTrendsAGITool(client, "trendsagi_delete_everything", {})).rejects.toMatchObject({
      name: "TrendsAGIToolError",
      code: "UNKNOWN_TOOL",
    });
  });

  it("rejects invalid JSON and non-object arguments", async () => {
    const { client } = stubClient();
    await expect(runTrendsAGITool(client, "trendsagi_get_trend", "{oops")).rejects.toMatchObject({
      code: "INVALID_ARGUMENTS",
    });
    await expect(runTrendsAGITool(client, "trendsagi_get_trend", [1, 2])).rejects.toMatchObject({
      code: "INVALID_ARGUMENTS",
    });
  });

  it("rejects missing and invalid required arguments", async () => {
    const { client } = stubClient();
    await expect(runTrendsAGITool(client, "trendsagi_get_trend", {})).rejects.toMatchObject({
      code: "INVALID_ARGUMENTS",
    });
    await expect(
      runTrendsAGITool(client, "trendsagi_get_trend", { trend_id: "7" }),
    ).rejects.toMatchObject({ code: "INVALID_ARGUMENTS" });
  });
});
