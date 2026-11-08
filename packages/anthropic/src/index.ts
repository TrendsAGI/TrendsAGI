import type { AdsPreviewBody, TrendsAGI } from "@trendsagi/core";

export interface AnthropicTool {
  name: string;
  description: string;
  input_schema: {
    type: "object";
    properties: Record<string, unknown>;
    required?: string[];
    additionalProperties?: boolean;
  };
}

export const TRENDSAGI_ANTHROPIC_TOOL_NAMES = [
  "trendsagi_list_trends",
  "trendsagi_get_trend",
  "trendsagi_get_insights",
  "trendsagi_get_trend_dossier",
  "trendsagi_list_web_trends",
  "trendsagi_get_search_demand",
  "trendsagi_get_brand_momentum",
  "trendsagi_get_trend_creators",
  "trendsagi_ask_trend",
  "trendsagi_get_social_evidence",
  "trendsagi_get_social_evidence_credits",
  "trendsagi_list_recommendations",
  "trendsagi_preview_ads",
] as const;

export type TrendsAGIAnthropicToolName = (typeof TRENDSAGI_ANTHROPIC_TOOL_NAMES)[number];

export type TrendsAGIToolErrorCode = "UNKNOWN_TOOL" | "INVALID_ARGUMENTS";

export class TrendsAGIToolError extends Error {
  readonly code: TrendsAGIToolErrorCode;

  constructor(code: TrendsAGIToolErrorCode, message: string) {
    super(message);
    this.name = "TrendsAGIToolError";
    this.code = code;
  }
}

type ToolSpec = AnthropicTool;

const LIST_TRENDS: ToolSpec = {
  name: "trendsagi_list_trends",
  description:
    "List currently trending topics from TrendsAGI with measured volume, velocity and growth. Use this first to discover a trend ID before requesting insights or recommendations.",
  input_schema: {
    type: "object",
    properties: {
      category: { type: "string", description: "Filter by vertical, for example Technology or Beauty." },
      search: { type: "string", description: "Only return trends whose name matches this phrase." },
      limit: {
        type: "integer",
        minimum: 1,
        maximum: 100,
        description: "Number of trends to return. Defaults to 10.",
      },
      sort_by: {
        type: "string",
        enum: ["volume", "velocity", "growth", "timestamp"],
        description: "Ranking field.",
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
  input_schema: {
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
  input_schema: {
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
  input_schema: {
    type: "object",
    properties: {
      limit: { type: "integer", minimum: 1, maximum: 100, description: "Number of recommendations to return." },
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
  input_schema: {
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

const GET_DOSSIER: ToolSpec = {
  name: "trendsagi_get_trend_dossier",
  description:
    "Read the source-backed dossier for one trend: resolved subject, evidence coverage, dated timeline, channels, content landscape, brands and products. Returns available=false when no dossier exists yet.",
  input_schema: {
    type: "object",
    properties: {
      trend_id: { type: "integer", minimum: 1, description: "Trend ID returned by trendsagi_list_trends." },
    },
    required: ["trend_id"],
    additionalProperties: false,
  },
};

const LIST_WEB_TRENDS: ToolSpec = {
  name: "trendsagi_list_web_trends",
  description:
    "List labels found in an external trend list, deduplicated and cached. Discovery evidence only: no measured volume or velocity. matched_trend_id links to a measured trend when one exists.",
  input_schema: {
    type: "object",
    properties: {
      limit: { type: "integer", minimum: 1, maximum: 200, description: "Number of discoveries to return. Defaults to 20." },
    },
    additionalProperties: false,
  },
};

const GET_SEARCH_DEMAND: ToolSpec = {
  name: "trendsagi_get_search_demand",
  description:
    "Read the stored relative search-interest series and related queries for one trend. Interest is a 0-100 index, not an absolute search volume.",
  input_schema: {
    type: "object",
    properties: {
      trend_id: { type: "integer", minimum: 1 },
      geo: { type: "string", description: "Two-letter market code. Default: US." },
    },
    required: ["trend_id"],
    additionalProperties: false,
  },
};

const GET_BRAND_MOMENTUM: ToolSpec = {
  name: "trendsagi_get_brand_momentum",
  description:
    "Read which brands are visible in a trend's coverage and how their share of that coverage moved. Share of coverage, not market share.",
  input_schema: {
    type: "object",
    properties: {
      trend_id: { type: "integer", minimum: 1 },
      window: { type: "string", enum: ["24h", "7d", "30d"] },
    },
    required: ["trend_id"],
    additionalProperties: false,
  },
};

const GET_TREND_CREATORS: ToolSpec = {
  name: "trendsagi_get_trend_creators",
  description: "List the accounts posting most about a trend. Posting activity, not influence.",
  input_schema: {
    type: "object",
    properties: {
      trend_id: { type: "integer", minimum: 1 },
    },
    required: ["trend_id"],
    additionalProperties: false,
  },
};

const ASK_TREND: ToolSpec = {
  name: "trendsagi_ask_trend",
  description:
    "Ask a grounded question about one trend. Returns an answer with numbered citations; grounded=false means the captured evidence was insufficient.",
  input_schema: {
    type: "object",
    properties: {
      trend_id: { type: "integer", minimum: 1 },
      question: { type: "string", description: "Question about the trend." },
    },
    required: ["trend_id", "question"],
    additionalProperties: false,
  },
};

const GET_SOCIAL_EVIDENCE: ToolSpec = {
  name: "trendsagi_get_social_evidence",
  description:
    "Read the stored Social Evidence report for a trend: posts, transcripts, creators, comments, ads, sponsors, hashtags and brand mentions. Free to read; returns available=false when no report exists yet.",
  input_schema: {
    type: "object",
    properties: {
      trend_id: { type: "integer", minimum: 1 },
    },
    required: ["trend_id"],
    additionalProperties: false,
  },
};

const GET_SOCIAL_EVIDENCE_CREDITS: ToolSpec = {
  name: "trendsagi_get_social_evidence_credits",
  description:
    "Read the account's Social Evidence credit balance, included allowance and available one-time packs. Free; does not consume a credit.",
  input_schema: {
    type: "object",
    properties: {},
    additionalProperties: false,
  },
};

const TOOL_SPECS: readonly ToolSpec[] = [
  LIST_TRENDS,
  GET_TREND,
  GET_INSIGHTS,
  GET_DOSSIER,
  LIST_WEB_TRENDS,
  GET_SEARCH_DEMAND,
  GET_BRAND_MOMENTUM,
  GET_TREND_CREATORS,
  ASK_TREND,
  GET_SOCIAL_EVIDENCE,
  GET_SOCIAL_EVIDENCE_CREDITS,
  LIST_RECOMMENDATIONS,
  PREVIEW_ADS,
];

function specFor(name: string): ToolSpec {
  const spec = TOOL_SPECS.find((candidate) => candidate.name === name);
  if (!spec) {
    throw new TrendsAGIToolError(
      "UNKNOWN_TOOL",
      `Unknown TrendsAGI tool "${name}". Expected one of: ${TRENDSAGI_ANTHROPIC_TOOL_NAMES.join(", ")}.`,
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
      throw new TrendsAGIToolError("INVALID_ARGUMENTS", "Tool input must be valid JSON.");
    }
  }
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    throw new TrendsAGIToolError("INVALID_ARGUMENTS", "Tool input must be a JSON object.");
  }
  return value as Record<string, unknown>;
}

function assertRequired(spec: ToolSpec, args: Record<string, unknown>): void {
  for (const key of spec.input_schema.required ?? []) {
    if (args[key] === undefined || args[key] === null) {
      throw new TrendsAGIToolError("INVALID_ARGUMENTS", `Argument "${key}" is required.`);
    }
  }
}

/**
 * Build Anthropic tool definitions for the TrendsAGI client.
 *
 * The `client` argument is accepted for API symmetry and future filtering; the
 * definitions themselves are static JSON Schema, so it is optional.
 */
export function createAnthropicTools(_client?: TrendsAGI): AnthropicTool[] {
  return TOOL_SPECS.map((spec) => ({
    name: spec.name,
    description: spec.description,
    input_schema: spec.input_schema,
  }));
}

/**
 * Validate a tool name, parse its input and execute it against TrendsAGI.
 * Returns JSON-serializable data for a `tool_result` content block.
 */
export async function runAnthropicTool(
  client: TrendsAGI,
  name: string,
  input: unknown,
): Promise<unknown> {
  const spec = specFor(name);
  const parsed = parseArguments(input);
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

    case "trendsagi_get_trend_dossier": {
      const trendId = integer(parsed, "trend_id", true) as number;
      const dossier = await client.trends.dossier(trendId);
      return dossier ?? { trend_id: trendId, available: false };
    }

    case "trendsagi_list_web_trends":
      return client.trends.discoveries({ limit: integer(parsed, "limit", false) });

    case "trendsagi_get_search_demand":
      return client.trends.searchDemand(integer(parsed, "trend_id", true) as number, {
        geo: optionalString(parsed, "geo"),
      });

    case "trendsagi_get_brand_momentum":
      return client.trends.brandMomentum(integer(parsed, "trend_id", true) as number, {
        window: optionalString(parsed, "window"),
      });

    case "trendsagi_get_trend_creators":
      return client.trends.creators(integer(parsed, "trend_id", true) as number);

    case "trendsagi_ask_trend":
      return client.trends.ask(
        integer(parsed, "trend_id", true) as number,
        optionalString(parsed, "question") as string,
      );

    case "trendsagi_get_social_evidence": {
      const trendId = integer(parsed, "trend_id", true) as number;
      const report = await client.trends.socialEvidence(trendId);
      return report ?? { trend_id: trendId, available: false };
    }

    case "trendsagi_get_social_evidence_credits":
      return client.credits.socialEvidence();

    case "trendsagi_preview_ads": {
      const platform = optionalString(parsed, "platform");
      if (!platform) {
        throw new TrendsAGIToolError("INVALID_ARGUMENTS", 'Argument "platform" is required.');
      }
      const body: AdsPreviewBody = {
        trend_id: integer(parsed, "trend_id", true) as number,
        apply_level: optionalString(parsed, "apply_level"),
        account_id: optionalString(parsed, "account_id"),
        campaign_id: optionalString(parsed, "campaign_id"),
        ad_group_id: optionalString(parsed, "ad_group_id"),
        ad_id: optionalString(parsed, "ad_id"),
        strict_safety: optionalBoolean(parsed, "strict_safety"),
      };
      return client.ads.preview(platform, body);
    }
  }
}
