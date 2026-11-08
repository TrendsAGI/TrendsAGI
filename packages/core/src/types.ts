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
  /** Comma-separated attachments; `dossier` attaches the compact resolved entity. */
  include?: string;
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

/* -------------------------------------------------------------------------- */
/* Dossiers, discovery, Deep Dive and Social Evidence                          */
/* -------------------------------------------------------------------------- */

export interface TrendListParamsWithInclude extends TrendListParams {
  /** Comma-separated attachments; `dossier` attaches the compact resolved entity. */
  include?: string;
}

export interface DossierEntity {
  subject_identified?: boolean;
  subject?: string | null;
  subject_type?: string | null;
  definition?: string | null;
  aliases?: string[];
  authoritative_url?: string | null;
  confidence?: number;
  other_meanings?: string[];
  [key: string]: unknown;
}

export interface DossierCoverage {
  status?: string | null;
  source_count?: number;
  domain_count?: number;
  dated_count?: number;
  freshest_at?: string | null;
  oldest_at?: string | null;
  high_authority?: number;
  mid_authority?: number;
  low_authority?: number;
  captured_at?: string | null;
  [key: string]: unknown;
}

export interface DossierEvent {
  at?: string | null;
  headline: string;
  detail?: string | null;
  event_type?: string | null;
  source_n?: number | null;
  source_url?: string | null;
  source_title?: string | null;
  [key: string]: unknown;
}

export interface DossierChannel {
  platform?: string | null;
  name: string;
  url?: string | null;
  channel_type?: string | null;
  evidence_n?: number | null;
  source_url?: string | null;
  [key: string]: unknown;
}

export interface DossierSerpResult {
  query?: string | null;
  title: string;
  url: string;
  site?: string | null;
  published?: string | null;
  format?: string | null;
  angle?: string | null;
  [key: string]: unknown;
}

export interface DossierContentLandscape {
  queries?: string[];
  results?: DossierSerpResult[];
  questions?: string[];
  gaps?: string[];
  outline?: string[];
  [key: string]: unknown;
}

export interface DossierBrand {
  name: string;
  presence?: string | null;
  sentiment?: string | null;
  source_n?: number | null;
  source_url?: string | null;
  [key: string]: unknown;
}

export interface DossierProduct {
  name: string;
  marketplace?: string | null;
  price?: string | null;
  source_n?: number | null;
  source_url?: string | null;
  [key: string]: unknown;
}

export interface DossierDelta {
  previous_captured_at?: string | null;
  new_events?: DossierEvent[];
  new_channels?: DossierChannel[];
  new_brands?: DossierBrand[];
  [key: string]: unknown;
}

export interface TrendDossier {
  trend_id: number;
  status: string;
  prompt_version?: string | null;
  model?: string | null;
  captured_at?: string | null;
  expires_at?: string | null;
  entity?: DossierEntity | null;
  coverage?: DossierCoverage | null;
  timeline?: DossierEvent[];
  channels?: DossierChannel[];
  content_landscape?: DossierContentLandscape | null;
  brands?: DossierBrand[];
  products?: DossierProduct[];
  delta?: DossierDelta | null;
  [key: string]: unknown;
}

export interface TrendDiscovery {
  source?: string | null;
  region?: string | null;
  label: string;
  rank?: number | null;
  first_seen_at?: string | null;
  last_seen_at?: string | null;
  seen_count?: number | null;
  matched_trend_id?: number | null;
  matched_name?: string | null;
  [key: string]: unknown;
}

export interface TrendDiscoveryListResponse {
  discoveries: TrendDiscovery[];
  [key: string]: unknown;
}

export type DeepDiveModule = "search_demand" | "ads" | "creators" | (string & {});

export interface SearchDemandPoint {
  captured_at?: string | null;
  interest: number;
  [key: string]: unknown;
}

export interface RelatedQuery {
  query: string;
  kind?: string | null;
  score?: number | null;
  [key: string]: unknown;
}

export interface SearchDemandResponse {
  geo?: string | null;
  query?: string | null;
  label?: string | null;
  series: SearchDemandPoint[];
  related: RelatedQuery[];
  divergence?: string | null;
  [key: string]: unknown;
}

export interface AdCreativeItem {
  platform?: string | null;
  advertiser?: string | null;
  ad_id: string;
  headline?: string | null;
  body?: string | null;
  cta?: string | null;
  landing_url?: string | null;
  started_at?: string | null;
  source_url?: string | null;
  angle?: string | null;
  [key: string]: unknown;
}

export interface CreatorLeaderboardRow {
  screen_name: string;
  followers_count?: number | null;
  posts?: number;
  latest_post_snippet?: string | null;
  profile_url?: string | null;
  [key: string]: unknown;
}

export interface CreatorLeaderboardResponse {
  trend_id: number;
  label?: string | null;
  creators: CreatorLeaderboardRow[];
  [key: string]: unknown;
}

export interface BrandMomentumRow {
  name: string;
  mentions?: number;
  share?: number;
  sentiment?: string | null;
  delta?: number | null;
  sparkline?: number[];
  [key: string]: unknown;
}

export interface BrandSnapshotRow {
  name: string;
  presence?: string | null;
  sentiment?: string | null;
  source_url?: string | null;
  [key: string]: unknown;
}

export interface BrandMomentumResponse {
  window?: string | null;
  captures?: number;
  label?: string | null;
  brands: BrandMomentumRow[];
  snapshot_brands?: BrandSnapshotRow[];
  [key: string]: unknown;
}

export interface EnrichTrendBody {
  modules?: DeepDiveModule[];
  region?: string;
  force?: boolean;
  request_id?: string;
  [key: string]: unknown;
}

export interface DeepDiveCreditsRemaining {
  included?: number;
  purchased?: number;
  resets_at?: string | null;
  daily_used?: number;
  daily_limit?: number;
  [key: string]: unknown;
}

export interface DeepDiveTopup {
  plan?: string | null;
  packs?: unknown;
  headline?: string | null;
  body?: string | null;
  upgrade_plan?: string | null;
  upgrade_label?: string | null;
  fallback_copy?: string | null;
  [key: string]: unknown;
}

export interface EnrichTrendResponse {
  trend_id?: number | null;
  request_id?: string | null;
  status?: string | null;
  credits_charged?: number;
  credits_remaining?: DeepDiveCreditsRemaining | null;
  data?: Record<string, unknown>;
  search_demand?: SearchDemandResponse | null;
  ads?: AdCreativeItem[];
  creators?: CreatorLeaderboardResponse | null;
  quality?: Record<string, unknown> | null;
  refreshed_at?: string | null;
  cache_age_seconds?: number | null;
  message?: string | null;
  topup?: DeepDiveTopup | null;
  [key: string]: unknown;
}

export interface AskTrendBody {
  question: string;
  [key: string]: unknown;
}

export interface AskTrendCitation {
  n: number;
  title: string;
  url?: string | null;
  source_type?: string | null;
  [key: string]: unknown;
}

export interface AskTrendEvidence {
  kind?: string | null;
  label?: string | null;
  count?: number;
  [key: string]: unknown;
}

export interface AskTrendResponse {
  answer: string;
  citations: AskTrendCitation[];
  grounded: boolean;
  generated_at?: string | null;
  evidence?: AskTrendEvidence[];
  follow_ups?: string[];
  insufficient_evidence_reason?: string | null;
  [key: string]: unknown;
}

export type SocialEvidenceModule =
  | "posts"
  | "transcripts"
  | "creators"
  | "comments"
  | "ads"
  | "sponsors"
  | "hashtags"
  | "mentions"
  | (string & {});

export interface RunSocialEvidenceBody {
  modules?: SocialEvidenceModule[];
  region?: string;
  force?: boolean;
  request_id?: string;
  [key: string]: unknown;
}

export interface SocialEvidenceIncludedCredits {
  remaining?: number;
  total?: number;
  resets_at?: string | null;
  [key: string]: unknown;
}

export interface SocialEvidencePurchasedCredits {
  remaining?: number;
  [key: string]: unknown;
}

export interface SocialEvidenceCreditPack {
  id: string;
  credits?: number;
  price?: string | null;
  lookup_key?: string | null;
  apple_product_id?: string | null;
  [key: string]: unknown;
}

export interface SocialEvidenceUpsell {
  headline?: string | null;
  body?: string | null;
  primary_pack?: string | null;
  upgrade_plan?: string | null;
  upgrade_label?: string | null;
  fallback_copy?: string | null;
  [key: string]: unknown;
}

export interface SocialEvidenceCreditBalance {
  plan?: string | null;
  included: SocialEvidenceIncludedCredits;
  purchased: SocialEvidencePurchasedCredits;
  packs: SocialEvidenceCreditPack[];
  upsell: SocialEvidenceUpsell;
  [key: string]: unknown;
}

export interface SocialEvidenceCreditsRemaining {
  included?: number;
  purchased?: number;
  resets_at?: string | null;
  [key: string]: unknown;
}

export interface SocialEvidenceQuality {
  completeness?: string | null;
  as_of?: string | null;
  source_count?: number;
  sections_present?: number;
  [key: string]: unknown;
}

export interface SocialEvidenceSection {
  present: boolean;
  sample_size?: number;
  items?: unknown[];
  tags?: Array<Record<string, unknown>>;
  themes?: Array<Record<string, unknown>>;
  angle_groups?: Array<Record<string, unknown>>;
  source_count?: number | null;
  [key: string]: unknown;
}

export interface SocialEvidenceReport {
  trend_id: number;
  status: string;
  refreshed_at?: string | null;
  credits_charged?: number;
  credits_remaining: SocialEvidenceCreditsRemaining;
  sections: Record<string, SocialEvidenceSection>;
  quality: SocialEvidenceQuality;
  topup?: SocialEvidenceUpsell | null;
  message?: string | null;
  error_code?: string | null;
  [key: string]: unknown;
}

export interface SocialEvidenceCheckoutBody {
  pack_id: string;
  success_url?: string;
  cancel_url?: string;
  [key: string]: unknown;
}

export interface SocialEvidenceCheckoutResponse {
  checkout_url: string;
  session_id?: string | null;
  pack?: SocialEvidenceCreditPack | null;
  [key: string]: unknown;
}
