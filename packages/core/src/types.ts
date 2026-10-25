/**
 * Public response and request types for the TrendsAGI REST API.
 *
 * The shapes mirror the first-party Python SDK and the generated OpenAPI
 * document at the repository root. Unknown fields are preserved in the index
 * signatures so a newer API deployment never breaks a typed consumer.
 */

export type TrendSortBy =
  | "volume"
  | "velocity"
  | "growth"
  | "timestamp"
  | "category"
  | "name"
  | (string & {});

export type SortDirection = "asc" | "desc";

export type TrendPeriod = "1h" | "4h" | "24h" | "7d" | "30d" | "90d" | "all" | (string & {});

export type AdsApplyLevel = "campaign" | "ad_group" | "ad" | (string & {});

export type RecommendationType =
  | "pr_response"
  | "content_idea"
  | "marketing_angle"
  | "seo_optimization"
  | "influencer_collab"
  | "product_improvement"
  | "crm_strategy"
  | "monitoring"
  | "other"
  | (string & {});

export type RecommendationPriority = "low" | "medium" | "high" | "critical" | "all" | (string & {});

export type RecommendationStatus = "new" | "viewed" | "actioned" | "dismissed" | "all" | (string & {});

export type AdsPlatform =
  | "google_ads"
  | "meta_ads"
  | "tiktok_ads"
  | "linkedin_ads"
  | "microsoft_ads"
  | "snapchat_ads"
  | "pinterest_ads"
  | (string & {});

export type QueryPrimitive = string | number | boolean | Date;

export type QueryValue =
  | QueryPrimitive
  | null
  | undefined
  | readonly QueryPrimitive[];

/** Query parameters accepted by `TrendsAGI.request`. */
export type QueryParams = Record<string, QueryValue>;

export interface TrendsAGIOptions {
  /** API key. Defaults to `TRENDSAGI_API_KEY`. */
  apiKey?: string;
  /** API origin. Defaults to `https://api.trendsagi.com`. */
  baseUrl?: string;
  /** Injectable fetch implementation, useful for tests and edge runtimes. */
  fetch?: typeof fetch;
  /** Headers merged into every request. */
  headers?: Record<string, string>;
  /** Send the key as `Authorization: Bearer` (default) or `X-API-Key`. */
  authScheme?: "bearer" | "x-api-key";
}

export type RequestOptions = Omit<RequestInit, "body" | "headers" | "method"> & {
  method?: string;
  /** JSON-serializable request body. */
  body?: unknown;
  /** Query parameters. `undefined`, `null` and empty arrays are omitted. */
  query?: QueryParams;
  headers?: HeadersInit;
  signal?: AbortSignal | null;
};

export interface PaginationMeta {
  total: number;
  limit: number;
  offset: number;
  [key: string]: unknown;
}

/* -------------------------------------------------------------------------- */
/* Trends                                                                      */
/* -------------------------------------------------------------------------- */

export interface Trend {
  id?: number;
  name?: string;
  volume?: number | null;
  timestamp?: string | null;
  category?: string | null;
  sentiment?: string | null;
  sentiment_category?: string | null;
  type?: string | null;
  meta_description?: string | null;
  /** Percentage growth over the comparison window. */
  growth?: number | null;
  previous_volume?: number | null;
  absolute_change?: number | null;
  /** Average velocity in posts per hour over recent snapshots. */
  average_velocity?: number | null;
  /** Standard deviation of volume over recent snapshots; lower is steadier. */
  trend_stability?: number | null;
  overall_trend?: string | null;
  [key: string]: unknown;
}

export interface TrendListResponse {
  trends: Trend[];
  total?: number;
  results?: Trend[] | null;
  meta?: PaginationMeta | null;
  [key: string]: unknown;
}

export interface TrendListParams {
  page?: number;
  limit?: number;
  offset?: number;
  sort_by?: TrendSortBy;
  sort_dir?: SortDirection;
  period?: TrendPeriod;
  start_date?: string;
  end_date?: string;
  min_snapshots?: number;
  exclude_sentiment?: string;
  /** Comma-separated or array form; arrays are serialized as `a,b`. */
  interests?: string[] | string;
  category?: string;
  search?: string;
  signal?: AbortSignal;
}

export interface SnapshotData {
  timestamp: string;
  volume?: number | null;
  [key: string]: unknown;
}

export interface TrendAnalyticsParams {
  /** Lookback window such as `1h`, `24h`, `7d` or `30d`. Defaults to the API default. */
  period?: TrendPeriod;
  signal?: AbortSignal;
}

export interface TrendAnalyticsResponse {
  trend_id: number;
  name: string;
  period: string;
  current_volume?: number | null;
  previous_volume?: number | null;
  volume_change_percent?: number | null;
  data: SnapshotData[];
  velocity_per_hour?: number | null;
  velocity_trend?: string | null;
  [key: string]: unknown;
}

export interface AutocompleteResult {
  name: string;
  count?: number;
  [key: string]: unknown;
}

export interface AutocompleteResponse {
  results: AutocompleteResult[];
  /** Convenience alias for the result names when the API returns objects. */
  suggestions?: string[];
  [key: string]: unknown;
}

export interface CategoryInfo {
  name: string;
  trend_count?: number;
  id?: number | null;
  slug?: string | null;
  description?: string | null;
  [key: string]: unknown;
}

export interface CategoryListResponse {
  categories: CategoryInfo[];
  [key: string]: unknown;
}

/* -------------------------------------------------------------------------- */
/* Insights                                                                    */
/* -------------------------------------------------------------------------- */

export interface TrendMetrics {
  velocity_score?: number | null;
  velocity_1h?: number | null;
  predicted_cpc_usd?: number | null;
  commercial_intent?: number | null;
  [key: string]: unknown;
}

export interface PlatformSignal {
  primary_source?: string | null;
  virality_distribution?: Record<string, number>;
  [key: string]: unknown;
}

export interface AudienceInjection {
  demographics?: Record<string, unknown>;
  interest_keywords?: string[];
  negative_keywords?: string[];
  platform_payloads?: Record<string, unknown>;
  [key: string]: unknown;
}

export interface BrandSafety {
  level?: string | null;
  flags?: string[];
  [key: string]: unknown;
}

export interface AIInsight {
  trend_id: number;
  trend_name?: string | null;
  sentiment_summary?: string | null;
  sentiment_category?: string | null;
  key_themes?: string[];
  content_brief?: Record<string, unknown>;
  ad_platform_targeting?: Record<string, unknown>;
  trend_metrics?: TrendMetrics | null;
  platform_signal?: PlatformSignal | null;
  audience_injection?: AudienceInjection | null;
  brand_safety?: BrandSafety | null;
  crm_and_support_insights?: Record<string, unknown>;
  overall_topic_category_llm?: string | null;
  analysis_notes?: string | null;
  llm_model_used?: string | null;
  generated_at?: string | null;
  usage_count?: number | null;
  usage_limit?: number | null;
  [key: string]: unknown;
}

export interface InsightSearchParams {
  /** Free-text query across trend names, categories and cached insight content. */
  q?: string;
  /** Filter by semantic theme. */
  keyThemeContains?: string;
  sentimentCategory?: string;
  audienceKeyword?: string;
  /** 1-100. The API default is 20. */
  limit?: number;
  signal?: AbortSignal;
}

export interface InsightSearchResult {
  id?: number;
  title?: string;
  type?: string;
  category?: string;
  sentiment?: string;
  [key: string]: unknown;
}

export interface InsightSearchResponse {
  results?: InsightSearchResult[];
  trends?: Trend[];
  total?: number;
  meta?: PaginationMeta | null;
  [key: string]: unknown;
}

/* -------------------------------------------------------------------------- */
/* Recommendations                                                             */
/* -------------------------------------------------------------------------- */

export interface RecommendationEvidence {
  metric: string;
  label: string;
  value: unknown;
  unit?: string | null;
  interpretation?: string | null;
  source: string;
  source_url?: string | null;
  observed_at?: string | null;
  [key: string]: unknown;
}

/**
 * Evidence-completeness metadata, not a forecasted probability of success.
 */
export interface RecommendationConfidence {
  /** 0-100 evidence completeness score. */
  score: number;
  level: string;
  method: string;
  reasons?: string[];
  missing_signals?: string[];
  [key: string]: unknown;
}

export interface RecommendationExpectedBenefit {
  outcome: string;
  basis: string;
  measurement: string;
  [key: string]: unknown;
}

export interface RecommendationUrgency {
  level: string;
  window: string;
  reason: string;
  [key: string]: unknown;
}

export interface RecommendationDataQuality {
  status: string;
  freshness: string;
  snapshot_at?: string | null;
  evidence_count: number;
  missing_signals?: string[];
  [key: string]: unknown;
}

export interface RecommendationDecisionBrief {
  why_now: string;
  evidence: RecommendationEvidence[];
  confidence: RecommendationConfidence;
  expected_benefit: RecommendationExpectedBenefit;
  urgency: RecommendationUrgency;
  next_steps: string[];
  data_quality: RecommendationDataQuality;
  actionable: boolean;
  [key: string]: unknown;
}

export interface Recommendation {
  id: number;
  user_id: number;
  type: string;
  title: string;
  details: string;
  source_trend_id?: string | number | null;
  source_trend_name?: string | null;
  priority: string;
  status: string;
  created_at: string;
  updated_at: string;
  user_feedback?: string | null;
  decision_brief?: RecommendationDecisionBrief | null;
  [key: string]: unknown;
}

export interface RecommendationListResponse {
  recommendations: Recommendation[];
  meta: PaginationMeta;
  [key: string]: unknown;
}

export interface RecommendationListParams {
  limit?: number;
  offset?: number;
  /** Recommendation type, or `all`. */
  type?: RecommendationType;
  /** Case-insensitive source-trend name search, maximum 100 characters. */
  sourceTrendQ?: string;
  priority?: RecommendationPriority;
  /** `new` (default), `viewed`, `actioned`, `dismissed` or `all`. */
  status?: RecommendationStatus;
  match_user_interests?: boolean;
  sort?: "priority" | "newest" | (string & {});
  signal?: AbortSignal;
}

/* -------------------------------------------------------------------------- */
/* Ads                                                                         */
/* -------------------------------------------------------------------------- */

export interface AdsProvider {
  platform: string;
  display_name?: string;
  configured?: boolean;
  is_connected?: boolean;
  selection?: Record<string, unknown>;
  [key: string]: unknown;
}

export interface AdsProvidersResponse {
  providers: AdsProvider[];
  [key: string]: unknown;
}

export interface AdsResourcesParams {
  account_id?: string;
  campaign_id?: string;
  ad_group_id?: string;
  client_id?: string;
  signal?: AbortSignal;
}

export interface AdsResource {
  id: string;
  name?: string;
  [key: string]: unknown;
}

export interface AdsResourcesResponse {
  accounts?: AdsResource[];
  campaigns?: AdsResource[];
  ad_groups?: AdsResource[];
  ads?: AdsResource[];
  [key: string]: unknown;
}

export interface AdsPreviewBody {
  /** Required positive trend ID. */
  trend_id: number;
  apply_level?: AdsApplyLevel;
  account_id?: string;
  campaign_id?: string;
  ad_group_id?: string;
  ad_id?: string;
  strict_safety?: boolean;
  [key: string]: unknown;
}

export interface AdsPreviewChange {
  field: string;
  before?: unknown;
  after?: unknown;
  [key: string]: unknown;
}

export interface AdsPreviewResponse {
  blocked?: boolean;
  target_ad_group_ids?: string[];
  changes?: AdsPreviewChange[];
  [key: string]: unknown;
}
