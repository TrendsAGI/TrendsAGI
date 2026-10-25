import { tool } from "@langchain/core/tools";
import { z } from "zod";
import type { AdsPreviewBody, TrendsAGI } from "@trendsagi/core";

const ADS_PLATFORMS = [
  "google_ads",
  "meta_ads",
  "tiktok_ads",
  "linkedin_ads",
  "microsoft_ads",
  "snapchat_ads",
  "pinterest_ads",
] as const;

const listTrendsSchema = z.object({
  category: z
    .string()
    .optional()
    .describe("Filter by vertical, for example Technology or Beauty."),
  search: z.string().optional().describe("Only return trends whose name matches this phrase."),
  limit: z
    .number()
    .int()
    .min(1)
    .max(100)
    .optional()
    .describe("Number of trends to return, 1-100."),
  sort_by: z
    .enum(["volume", "velocity", "growth", "timestamp"])
    .optional()
    .describe("Ranking field."),
  period: z
    .enum(["1h", "4h", "24h", "7d", "30d", "90d", "all"])
    .optional()
    .describe("Lookback window for the returned metrics."),
});

const trendIdSchema = z.object({
  trend_id: z
    .number()
    .int()
    .positive()
    .describe("Trend ID returned by list_trends."),
});

const listRecommendationsSchema = z.object({
  limit: z.number().int().min(1).max(100).optional().describe("Number of recommendations to return."),
  priority: z
    .enum(["low", "medium", "high", "critical", "all"])
    .optional()
    .describe("Filter by priority."),
  status: z
    .enum(["new", "viewed", "actioned", "dismissed", "all"])
    .optional()
    .describe("Filter by workflow status."),
  match_user_interests: z
    .boolean()
    .optional()
    .describe("Restrict results to the account's saved interests."),
});

const previewAdsSchema = z.object({
  platform: z.enum(ADS_PLATFORMS).describe("Connected ads platform identifier."),
  trend_id: z
    .number()
    .int()
    .positive()
    .describe("Trend ID that supplies the proposed targeting."),
  apply_level: z
    .enum(["campaign", "ad_group", "ad"])
    .optional()
    .describe("Level the preview applies to."),
  account_id: z.string().optional(),
  campaign_id: z.string().optional(),
  ad_group_id: z.string().optional(),
  ad_id: z.string().optional(),
  strict_safety: z.boolean().optional(),
});

/**
 * Build LangChain tools for a TrendsAGI client.
 *
 * Every tool returns JSON-serializable data, so it can go straight back into a
 * tool message. `preview_ads` only previews changes; it never applies them.
 */
export function createTrendsAGITools(client: TrendsAGI) {
  return [
    tool(
      async ({ category, search, limit, sort_by, period }) =>
        client.trends.list({ category, search, limit, sort_by, period }),
      {
        name: "list_trends",
        description:
          "List currently trending topics from TrendsAGI with measured volume, velocity and growth. Use this first to discover a trend ID.",
        schema: listTrendsSchema,
      },
    ),
    tool(
      async ({ trend_id }) => {
        const insight = await client.insights.get(trend_id);
        return insight ?? { trend_id, available: false };
      },
      {
        name: "get_trend_insights",
        description:
          "Read cached AI insights for one trend: sentiment summary, key themes, marketing angle and audience targeting. Read-only.",
        schema: trendIdSchema,
      },
    ),
    tool(
      async ({ limit, priority, status, match_user_interests }) =>
        client.recommendations.list({ limit, priority, status, match_user_interests }),
      {
        name: "list_recommendations",
        description:
          "List prioritized, evidence-backed TrendsAGI recommendations with decision briefs, confidence (evidence completeness) and next steps.",
        schema: listRecommendationsSchema,
      },
    ),
    tool(
      async ({ platform, trend_id, apply_level, account_id, campaign_id, ad_group_id, ad_id, strict_safety }) => {
        const body: AdsPreviewBody = {
          trend_id,
          apply_level,
          account_id,
          campaign_id,
          ad_group_id,
          ad_id,
          strict_safety,
        };
        return client.ads.preview(platform, body);
      },
      {
        name: "preview_ads",
        description:
          "Preview additive keyword or targeting updates for a connected ads platform before anything is applied. Never applies changes.",
        schema: previewAdsSchema,
      },
    ),
  ];
}
