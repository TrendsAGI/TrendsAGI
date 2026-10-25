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
    trends: { list: record("trends.list"), get: record("trends.get") },
    insights: { get: record("insights.get") },
    recommendations: { list: record("recommendations.list") },
    ads: { preview: record("ads.preview") },
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
    expect(createAnthropicTools(client)).toHaveLength(5);
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
