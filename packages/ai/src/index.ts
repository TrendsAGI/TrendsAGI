import { tool } from "ai";
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
  trend_id: z.number().int().positive().describe("Trend ID returned by list_trends."),
});

const discoveriesSchema = z.object({
  limit: z.number().int().min(1).max(200).optional().describe("Number of discoveries to return."),
});

const searchDemandSchema = z.object({
  trend_id: z.number().int().positive().describe("Trend ID."),
  geo: z.string().optional().describe("Two-letter market code. Default: US."),
});

const brandMomentumSchema = z.object({
  trend_id: z.number().int().positive().describe("Trend ID."),
  window: z.enum(["24h", "7d", "30d"]).optional().describe("Comparison window."),
});

const askTrendSchema = z.object({
  trend_id: z.number().int().positive().describe("Trend ID."),
  question: z.string().describe("Question about the trend."),
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
  trend_id: z.number().int().positive().describe("Trend ID that supplies the proposed targeting."),
  apply_level: z.enum(["campaign", "ad_group", "ad"]).optional(),
  account_id: z.string().optional(),
  campaign_id: z.string().optional(),
  ad_group_id: z.string().optional(),
  ad_id: z.string().optional(),
  strict_safety: z.boolean().optional(),
});

/**
 * Build Vercel AI SDK tools for a TrendsAGI client.
 *
 * Pass the result straight to `generateText({ tools })` or `streamText`.
 * `preview_ads` only previews changes; it never applies them.
 */
export function createTrendsAGITools(client: TrendsAGI) {
  return {
    list_trends: tool({
      description:
        "List currently trending topics from TrendsAGI with measured volume, velocity and growth. Use this first to discover a trend ID.",
      inputSchema: listTrendsSchema,
      execute: async ({ category, search, limit, sort_by, period }) =>
        client.trends.list({ category, search, limit, sort_by, period }),
    }),

    get_trend_insights: tool({
      description:
        "Read cached AI insights for one trend: sentiment summary, key themes, marketing angle and audience targeting. Read-only.",
      inputSchema: trendIdSchema,
      execute: async ({ trend_id }) => {
        const insight = await client.insights.get(trend_id);
        return insight ?? { trend_id, available: false };
      },
    }),

    list_recommendations: tool({
      description:
        "List prioritized, evidence-backed TrendsAGI recommendations with decision briefs, confidence (evidence completeness) and next steps.",
      inputSchema: listRecommendationsSchema,
      execute: async ({ limit, priority, status, match_user_interests }) =>
        client.recommendations.list({ limit, priority, status, match_user_interests }),
    }),

    get_trend_dossier: tool({
      description:
        "Read the source-backed dossier for one trend: resolved subject, timeline, channels, content landscape, brands and products. Returns available=false when none exists.",
      inputSchema: trendIdSchema,
      execute: async ({ trend_id }) => {
        const dossier = await client.trends.dossier(trend_id);
        return dossier ?? { trend_id, available: false };
      },
    }),

    list_web_trends: tool({
      description:
        "List labels found in an external trend list. Discovery evidence only: no measured volume or velocity.",
      inputSchema: discoveriesSchema,
      execute: async ({ limit }) => client.trends.discoveries({ limit }),
    }),

    get_search_demand: tool({
      description:
        "Read the stored relative search-interest series and related queries. Interest is a 0-100 index, not absolute search volume.",
      inputSchema: searchDemandSchema,
      execute: async ({ trend_id, geo }) => client.trends.searchDemand(trend_id, { geo }),
    }),

    get_brand_momentum: tool({
      description:
        "Read which brands are visible in a trend's coverage and how their share of that coverage moved. Share of coverage, not market share.",
      inputSchema: brandMomentumSchema,
      execute: async ({ trend_id, window }) => client.trends.brandMomentum(trend_id, { window }),
    }),

    get_trend_creators: tool({
      description: "List the accounts posting most about a trend. Posting activity, not influence.",
      inputSchema: trendIdSchema,
      execute: async ({ trend_id }) => client.trends.creators(trend_id),
    }),

    ask_trend: tool({
      description:
        "Ask a grounded question about one trend. Returns an answer with numbered citations; grounded=false means the evidence was insufficient.",
      inputSchema: askTrendSchema,
      execute: async ({ trend_id, question }) => client.trends.ask(trend_id, question),
    }),

    get_social_evidence: tool({
      description:
        "Read the stored Social Evidence report for a trend: posts, transcripts, creators, comments, ads, sponsors, hashtags and brand mentions. Free to read.",
      inputSchema: trendIdSchema,
      execute: async ({ trend_id }) => {
        const report = await client.trends.socialEvidence(trend_id);
        return report ?? { trend_id, available: false };
      },
    }),

    get_social_evidence_credits: tool({
      description:
        "Read the account's Social Evidence credit balance, included allowance and available one-time packs. Free.",
      inputSchema: z.object({}),
      execute: async () => client.credits.socialEvidence(),
    }),

    preview_ads: tool({
      description:
        "Preview additive keyword or targeting updates for a connected ads platform before anything is applied. Never applies changes.",
      inputSchema: previewAdsSchema,
      execute: async ({
        platform,
        trend_id,
        apply_level,
        account_id,
        campaign_id,
        ad_group_id,
        ad_id,
        strict_safety,
      }) => {
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
    }),
  };
}
