import type { AdsPreviewBody, TrendsAGI } from "@trendsagi/core";

/**
 * A minimal JSON Schema subset used by OpenAI function tools.
 * No JSON Schema library is required at runtime.
 */
export interface JsonSchema {
  type?: "object" | "string" | "integer" | "number" | "boolean" | "array";
  description?: string;
  properties?: Record<string, JsonSchema>;
  required?: readonly string[];
  enum?: readonly (string | number | boolean)[];
  items?: JsonSchema;
  minimum?: number;
  maximum?: number;
  default?: unknown;
  additionalProperties?: boolean;
}

export type OpenAIToolFormat = "responses" | "chat";

export interface OpenAIResponsesTool {
  type: "function";
  name: string;
  description: string;
  parameters: JsonSchema;
}

export interface OpenAIChatTool {
  type: "function";
  function: {
    name: string;
    description: string;
    parameters: JsonSchema;
  };
}

export type OpenAITool = OpenAIResponsesTool | OpenAIChatTool;

export interface CreateOpenAIToolsOptions {
  /** `responses` (default) matches `openai.responses.create`; `chat` matches `chat.completions.create`. */
  format?: OpenAIToolFormat;
}

export const TRENDSAGI_OPENAI_TOOL_NAMES = [
  "trendsagi_list_trends",
  "trendsagi_get_trend",
  "trendsagi_get_insights",
  "trendsagi_list_recommendations",
  "trendsagi_preview_ads",
] as const;

export type TrendsAGIToolName = (typeof TRENDSAGI_OPENAI_TOOL_NAMES)[number];

export type TrendsAGIToolErrorCode = "UNKNOWN_TOOL" | "INVALID_ARGUMENTS";

export class TrendsAGIToolError extends Error {
  readonly code: TrendsAGIToolErrorCode;

  constructor(code: TrendsAGIToolErrorCode, message: string) {
    super(message);
    this.name = "TrendsAGIToolError";
    this.code = code;
  }
}

type ToolSpec = {
  name: TrendsAGIToolName;
  description: string;
  parameters: JsonSchema;
};

const LIST_TRENDS: ToolSpec = {
  name: "trendsagi_list_trends",
  description:
    "List currently trending topics from TrendsAGI with measured volume, velocity and growth. Use this first to discover a trend ID before requesting insights or recommendations.",
  parameters: {
    type: "object",
    properties: {
      category: { type: "string", description: "Filter by vertical, for example Technology or Beauty." },
      search: { type: "string", description: "Only return trends whose name matches this phrase." },
      limit: { type: "integer", minimum: 1, maximum: 100, default: 10 },
      sort_by: {
        type: "string",
        enum: ["volume", "velocity", "growth", "timestamp"],
        description: "Ranking field. Defaults to the API default.",
      },
      period: {
        type: "string",
        enum: ["1h", "4h", "24h", "7d", "30d", "90d", "all"],
        description: "Lookback window for the returned metrics.",
      },
    },
    additionalProperties: false,
  },
};

const GET_TREND: ToolSpec = {
  name: "trendsagi_get_trend",
  description:
    "Retrieve the core record for one TrendsAGI signal: category, sentiment classification, timestamp and latest observed volume.",
  parameters: {
    type: "object",
    properties: {
      trend_id: { type: "integer", minimum: 1, description: "Trend ID returned by trendsagi_list_trends." },
    },
    required: ["trend_id"],
    additionalProperties: false,
  },
};

const GET_INSIGHTS: ToolSpec = {
  name: "trendsagi_get_insights",
  description:
    "Read cached AI insights for one trend: sentiment summary, key themes, marketing angle and audience targeting. Read-only; it does not start a new generation.",
  parameters: {
    type: "object",
    properties: {
      trend_id: { type: "integer", minimum: 1, description: "Trend ID to read insights for." },
    },
    required: ["trend_id"],
    additionalProperties: false,
  },
};

const LIST_RECOMMENDATIONS: ToolSpec = {
  name: "trendsagi_list_recommendations",
  description:
    "List prioritized, evidence-backed TrendsAGI recommendations with decision briefs, confidence (evidence completeness) and next steps.",
  parameters: {
    type: "object",
    properties: {
      limit: { type: "integer", minimum: 1, maximum: 100, default: 10 },
      priority: { type: "string", enum: ["low", "medium", "high", "critical", "all"] },
      status: { type: "string", enum: ["new", "viewed", "actioned", "dismissed", "all"] },
      type: {
        type: "string",
        enum: [
          "pr_response",
          "content_idea",
          "marketing_angle",
          "seo_optimization",
          "influencer_collab",
          "product_improvement",
          "crm_strategy",
          "monitoring",
          "other",
          "all",
        ],
      },
      match_user_interests: { type: "boolean" },
    },
    additionalProperties: false,
  },
};

const PREVIEW_ADS: ToolSpec = {
  name: "trendsagi_preview_ads",
  description:
    "Preview additive keyword or targeting updates for a connected ads platform before anything is applied. This never applies changes.",
  parameters: {
    type: "object",
    properties: {
      platform: {
        type: "string",
        enum: [
          "google_ads",
          "meta_ads",
          "tiktok_ads",
          "linkedin_ads",
          "microsoft_ads",
          "snapchat_ads",
          "pinterest_ads",
        ],
        description: "Connected ads platform identifier.",
      },
      trend_id: { type: "integer", minimum: 1, description: "Trend ID that supplies the proposed targeting." },
      apply_level: { type: "string", enum: ["campaign", "ad_group", "ad"] },
      account_id: { type: "string" },
      campaign_id: { type: "string" },
      ad_group_id: { type: "string" },
      ad_id: { type: "string" },
      strict_safety: { type: "boolean" },
    },
    required: ["platform", "trend_id"],
    additionalProperties: false,
  },
};

const TOOL_SPECS: readonly ToolSpec[] = [
  LIST_TRENDS,
  GET_TREND,
  GET_INSIGHTS,
  LIST_RECOMMENDATIONS,
  PREVIEW_ADS,
];

function specFor(name: string): ToolSpec {
  const spec = TOOL_SPECS.find((candidate) => candidate.name === name);
  if (!spec) {
    throw new TrendsAGIToolError(
      "UNKNOWN_TOOL",
      `Unknown TrendsAGI tool "${name}". Expected one of: ${TRENDSAGI_OPENAI_TOOL_NAMES.join(", ")}.`,
    );
  }
  return spec;
}

function optionalString(args: Record<string, unknown>, key: string): string | undefined {
  const value = args[key];
  if (value === undefined || value === null) return undefined;
  if (typeof value !== "string") {
    throw new TrendsAGIToolError("INVALID_ARGUMENTS", `Argument "${key}" must be a string.`);
  }
  return value;
}

function optionalBoolean(args: Record<string, unknown>, key: string): boolean | undefined {
  const value = args[key];
  if (value === undefined || value === null) return undefined;
  if (typeof value !== "boolean") {
    throw new TrendsAGIToolError("INVALID_ARGUMENTS", `Argument "${key}" must be a boolean.`);
  }
  return value;
}

function integer(args: Record<string, unknown>, key: string, required: boolean): number | undefined {
  const value = args[key];
  if (value === undefined || value === null) {
    if (required) {
      throw new TrendsAGIToolError("INVALID_ARGUMENTS", `Argument "${key}" is required.`);
    }
    return undefined;
  }
  if (typeof value !== "number" || !Number.isInteger(value) || value < 1) {
    throw new TrendsAGIToolError("INVALID_ARGUMENTS", `Argument "${key}" must be a positive integer.`);
  }
  return value;
}

function parseArguments(input: unknown): Record<string, unknown> {
  let value = input;
  if (typeof value === "string") {
    try {
      value = JSON.parse(value);
    } catch {
      throw new TrendsAGIToolError("INVALID_ARGUMENTS", "Tool arguments must be valid JSON.");
    }
  }
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    throw new TrendsAGIToolError("INVALID_ARGUMENTS", "Tool arguments must be a JSON object.");
  }
  return value as Record<string, unknown>;
}

function assertRequired(spec: ToolSpec, args: Record<string, unknown>): void {
  for (const key of spec.parameters.required ?? []) {
    if (args[key] === undefined || args[key] === null) {
      throw new TrendsAGIToolError("INVALID_ARGUMENTS", `Argument "${key}" is required.`);
    }
  }
}

/**
 * Build OpenAI function tools for the TrendsAGI client.
 *
 * The returned objects are plain data and do not require the OpenAI SDK.
 */
export function createOpenAITools(
  _client: TrendsAGI,
  options: CreateOpenAIToolsOptions = {},
): OpenAITool[] {
  const format = options.format ?? "responses";
  if (format !== "responses" && format !== "chat") {
    throw new TrendsAGIToolError(
      "INVALID_ARGUMENTS",
      `Unsupported tool format "${String(format)}". Use "responses" or "chat".`,
    );
  }
  return TOOL_SPECS.map((spec) =>
    format === "chat"
      ? {
          type: "function",
          function: {
            name: spec.name,
            description: spec.description,
            parameters: spec.parameters,
          },
        }
      : {
          type: "function",
          name: spec.name,
          description: spec.description,
          parameters: spec.parameters,
        },
  );
}

/**
 * Validate a tool name, parse its arguments and execute it against TrendsAGI.
 * Returns JSON-serializable data suitable for a tool-result message.
 */
export async function runTrendsAGITool(
  client: TrendsAGI,
  name: string,
  args: unknown,
): Promise<unknown> {
  const spec = specFor(name);
  const parsed = parseArguments(args);
  assertRequired(spec, parsed);

  switch (spec.name) {
    case "trendsagi_list_trends":
      return client.trends.list({
        category: optionalString(parsed, "category"),
        search: optionalString(parsed, "search"),
        limit: integer(parsed, "limit", false),
        sort_by: optionalString(parsed, "sort_by"),
        period: optionalString(parsed, "period"),
      });

    case "trendsagi_get_trend":
      return client.trends.get(integer(parsed, "trend_id", true) as number);

    case "trendsagi_get_insights": {
      const trendId = integer(parsed, "trend_id", true) as number;
      const insight = await client.insights.get(trendId);
      return insight ?? { trend_id: trendId, available: false };
    }

    case "trendsagi_list_recommendations":
      return client.recommendations.list({
        limit: integer(parsed, "limit", false),
        priority: optionalString(parsed, "priority"),
        status: optionalString(parsed, "status"),
        type: optionalString(parsed, "type"),
        match_user_interests: optionalBoolean(parsed, "match_user_interests"),
      });

    case "trendsagi_preview_ads": {
      const body: AdsPreviewBody = {
        trend_id: integer(parsed, "trend_id", true) as number,
        apply_level: optionalString(parsed, "apply_level"),
        account_id: optionalString(parsed, "account_id"),
        campaign_id: optionalString(parsed, "campaign_id"),
        ad_group_id: optionalString(parsed, "ad_group_id"),
        ad_id: optionalString(parsed, "ad_id"),
        strict_safety: optionalBoolean(parsed, "strict_safety"),
      };
      return client.ads.preview(optionalString(parsed, "platform") as string, body);
    }
  }
}
