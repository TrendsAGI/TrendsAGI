import { TrendsAGIError } from "./errors.js";
import type {
  AdsPlatform,
  AdsPreviewBody,
  AdsPreviewResponse,
  AdsProvidersResponse,
  AdsResourcesParams,
  AdsResourcesResponse,
  AIInsight,
  AskTrendResponse,
  AutocompleteResponse,
  AutocompleteResult,
  BrandMomentumResponse,
  CategoryListResponse,
  CreatorLeaderboardResponse,
  EnrichTrendBody,
  EnrichTrendResponse,
  InsightSearchParams,
  InsightSearchResponse,
  QueryParams,
  QueryPrimitive,
  RecommendationListParams,
  RecommendationListResponse,
  RequestOptions,
  RunSocialEvidenceBody,
  SearchDemandResponse,
  SocialEvidenceCheckoutBody,
  SocialEvidenceCheckoutResponse,
  SocialEvidenceCreditBalance,
  SocialEvidenceReport,
  Trend,
  TrendAnalyticsParams,
  TrendAnalyticsResponse,
  TrendDiscoveryListResponse,
  TrendDossier,
  TrendListParams,
  TrendListResponse,
  TrendsAGIOptions,
} from "./types.js";

const DEFAULT_BASE_URL = "https://api.trendsagi.com";
const USER_AGENT = "@trendsagi/core";

type Requester = {
  request<T>(path: string, init?: RequestOptions): Promise<T>;
};

function readEnv(name: string): string | undefined {
  try {
    if (typeof process === "undefined" || !process.env) return undefined;
    const value = process.env[name];
    return value && value.trim() ? value.trim() : undefined;
  } catch {
    return undefined;
  }
}

function normalizeBaseUrl(baseUrl: string): string {
  return baseUrl.replace(/\/+$/, "");
}

function serializePrimitive(value: QueryPrimitive): string {
  if (value instanceof Date) return value.toISOString();
  return String(value);
}

/**
 * Serialize a query object. `undefined`, `null` and empty arrays are omitted;
 * arrays become comma-separated values (`interests=a,b`) to match the REST API
 * and the Python SDK.
 */
export function buildQueryString(query?: QueryParams): string {
  if (!query) return "";
  const search = new URLSearchParams();
  for (const [key, rawValue] of Object.entries(query)) {
    if (rawValue === undefined || rawValue === null) continue;
    const values = Array.isArray(rawValue) ? rawValue : [rawValue];
    const serialized = values.map((value) => serializePrimitive(value as QueryPrimitive)).join(",");
    if (serialized === "") continue;
    search.append(key, serialized);
  }
  const value = search.toString();
  return value ? `?${value}` : "";
}

function buildUrl(baseUrl: string, path: string, query?: QueryParams): string {
  const isAbsolute = /^[a-z][a-z\d+\-.]*:\/\//i.test(path);
  const absolute = isAbsolute ? path : `${baseUrl}${path.startsWith("/") ? "" : "/"}${path}`;
  const queryString = buildQueryString(query);
  if (!queryString) return absolute;
  const url = new URL(absolute);
  const extra = new URLSearchParams(queryString);
  for (const [key, value] of extra) url.searchParams.append(key, value);
  return url.toString();
}

function extractDetail(payload: unknown): string | undefined {
  if (typeof payload === "string") {
    const trimmed = payload.trim();
    return trimmed || undefined;
  }
  if (!payload || typeof payload !== "object") return undefined;
  const record = payload as Record<string, unknown>;
  for (const key of ["detail", "message", "error_description", "error"]) {
    const value = record[key];
    if (typeof value === "string" && value.trim()) return value.trim();
    if (value && typeof value === "object") {
      const nested = extractDetail(value);
      if (nested) return nested;
    }
  }
  return undefined;
}

function isAbortError(error: unknown): boolean {
  return (
    error instanceof Error &&
    (error.name === "AbortError" || error.name === "TimeoutError")
  );
}

function isJsonContentType(contentType: string | null): boolean {
  return !!contentType && /(^|\s|;)application\/(?:[\w.+-]*\+)?json(?:\s|;|$)/i.test(contentType);
}

class TrendsNamespace {
  constructor(private readonly client: Requester) {}

  /** List currently trending topics. */
  list(params: TrendListParams = {}): Promise<TrendListResponse> {
    const { signal, ...query } = params;
    return this.client.request<TrendListResponse>("/api/trends", { query, signal });
  }

  /** Retrieve one trend by ID. */
  get(id: number | string): Promise<Trend> {
    return this.client.request<Trend>(`/api/trends/${encodeURIComponent(String(id))}`);
  }

  /** Retrieve snapshot analytics for one trend. */
  analytics(id: number | string, params: TrendAnalyticsParams = {}): Promise<TrendAnalyticsResponse> {
    const { signal, ...query } = params;
    return this.client.request<TrendAnalyticsResponse>(
      `/api/trends/${encodeURIComponent(String(id))}/analytics`,
      { query, signal },
    );
  }

  /** List the categories that currently have active trends. */
  async categories(): Promise<CategoryListResponse> {
    const response = await this.client.request<CategoryListResponse | CategoryListResponse["categories"]>(
      "/api/trends/categories",
    );
    if (Array.isArray(response)) return { categories: response };
    return { ...response, categories: response.categories ?? [] };
  }

  /** Autocomplete trend names for a query string. */
  async autocomplete(query: string): Promise<AutocompleteResponse> {
    const response = await this.client.request<AutocompleteResponse | Array<string | AutocompleteResult>>(
      "/api/trends/autocomplete",
      { query: { q: query } },
    );
    if (Array.isArray(response)) {
      const results = response.map((item) => (typeof item === "string" ? { name: item } : item));
      return { results, suggestions: results.map((item) => item.name) };
    }
    const results = response.results ?? [];
    return { ...response, results, suggestions: response.suggestions ?? results.map((item) => item.name) };
  }

  /** Retrieve the source-backed dossier for one trend, or null when none exists. */
  async dossier(id: number | string): Promise<TrendDossier | null> {
    try {
      return await this.client.request<TrendDossier>(
        `/api/trends/${encodeURIComponent(String(id))}/dossier`,
      );
    } catch (error) {
      if (error instanceof TrendsAGIError && error.status === 404) return null;
      throw error;
    }
  }

  /** List labels found in an external trend list. Discovery evidence only. */
  discoveries(params: { limit?: number; signal?: AbortSignal } = {}): Promise<TrendDiscoveryListResponse> {
    const { signal, ...query } = params;
    return this.client.request<TrendDiscoveryListResponse>("/api/trends/discoveries", {
      query,
      signal,
    });
  }

  /** Run an on-demand Deep Dive. Reserves credits only when usable live data is produced. */
  enrich(id: number | string, body: EnrichTrendBody = {}): Promise<EnrichTrendResponse> {
    return this.client.request<EnrichTrendResponse>(
      `/api/trends/${encodeURIComponent(String(id))}/enrich`,
      { method: "POST", body },
    );
  }

  /** Read the stored relative search-interest series and related queries. */
  searchDemand(
    id: number | string,
    params: { geo?: string; signal?: AbortSignal } = {},
  ): Promise<SearchDemandResponse> {
    const { signal, ...query } = params;
    return this.client.request<SearchDemandResponse>(
      `/api/trends/${encodeURIComponent(String(id))}/search-demand`,
      { query, signal },
    );
  }

  /** Read brands visible in a trend's coverage and their movement. */
  brandMomentum(
    id: number | string,
    params: { window?: "24h" | "7d" | "30d" | (string & {}); signal?: AbortSignal } = {},
  ): Promise<BrandMomentumResponse> {
    const { signal, ...query } = params;
    return this.client.request<BrandMomentumResponse>(
      `/api/trends/${encodeURIComponent(String(id))}/brand-momentum`,
      { query, signal },
    );
  }

  /** List the accounts posting most about a trend. */
  creators(id: number | string): Promise<CreatorLeaderboardResponse> {
    return this.client.request<CreatorLeaderboardResponse>(
      `/api/trends/${encodeURIComponent(String(id))}/creators`,
    );
  }

  /** Ask a grounded question about one trend. */
  ask(id: number | string, question: string): Promise<AskTrendResponse> {
    return this.client.request<AskTrendResponse>(
      `/api/trends/${encodeURIComponent(String(id))}/ask`,
      { method: "POST", body: { question } },
    );
  }

  /** Read the stored Social Evidence report, or null when none exists. */
  async socialEvidence(id: number | string): Promise<SocialEvidenceReport | null> {
    try {
      return await this.client.request<SocialEvidenceReport>(
        `/api/trends/${encodeURIComponent(String(id))}/social-evidence`,
      );
    } catch (error) {
      if (error instanceof TrendsAGIError && error.status === 404) return null;
      throw error;
    }
  }

  /** Run or refresh Social Evidence. Reserves one credit per run. */
  runSocialEvidence(
    id: number | string,
    body: RunSocialEvidenceBody = {},
  ): Promise<SocialEvidenceReport> {
    return this.client.request<SocialEvidenceReport>(
      `/api/trends/${encodeURIComponent(String(id))}/social-evidence`,
      { method: "POST", body },
    );
  }
}

class CreditsNamespace {
  constructor(private readonly client: Requester) {}

  /** Read the Social Evidence credit balance. Free. */
  socialEvidence(): Promise<SocialEvidenceCreditBalance> {
    return this.client.request<SocialEvidenceCreditBalance>("/api/user/social-evidence-credits");
  }

  /** Create a Stripe Checkout session for a Social Evidence credit pack. */
  buySocialEvidence(
    packId: string,
    params: { success_url?: string; cancel_url?: string } = {},
  ): Promise<SocialEvidenceCheckoutResponse> {
    const body: SocialEvidenceCheckoutBody = { pack_id: packId, ...params };
    return this.client.request<SocialEvidenceCheckoutResponse>(
      "/api/billing/social-evidence/checkout",
      { method: "POST", body },
    );
  }
}

class InsightsNamespace {
  constructor(private readonly client: Requester) {}

  /** Retrieve cached AI insights for one trend. Read-only; does not start generation. */
  get(trendId: number | string): Promise<AIInsight | null> {
    return this.client.request<AIInsight | null>(
      `/api/trends/${encodeURIComponent(String(trendId))}/ai-insights`,
    );
  }

  /** Search cached insight content and trend metadata. */
  search(params: InsightSearchParams = {}): Promise<InsightSearchResponse> {
    const { signal, ...query } = params;
    return this.client.request<InsightSearchResponse>("/api/insights/search", { query, signal });
  }
}

class RecommendationsNamespace {
  constructor(private readonly client: Requester) {}

  /** List prioritized, evidence-backed recommendations. */
  list(params: RecommendationListParams = {}): Promise<RecommendationListResponse> {
    const { signal, ...query } = params;
    return this.client.request<RecommendationListResponse>("/api/intelligence/recommendations", {
      query,
      signal,
    });
  }
}

class AdsNamespace {
  constructor(private readonly client: Requester) {}

  /** List connected ads providers and their saved selection metadata. */
  providers(): Promise<AdsProvidersResponse> {
    return this.client.request<AdsProvidersResponse>("/api/integrations/ads/providers");
  }

  /** List accounts, campaigns, ad groups and ads for one ads platform. */
  resources(platform: AdsPlatform, params: AdsResourcesParams = {}): Promise<AdsResourcesResponse> {
    const { signal, ...query } = params;
    return this.client.request<AdsResourcesResponse>(
      `/api/integrations/ads/${encodeURIComponent(platform)}/resources`,
      { query, signal },
    );
  }

  /** Preview additive keyword/targeting updates before applying them. */
  preview(platform: AdsPlatform, body: AdsPreviewBody): Promise<AdsPreviewResponse> {
    return this.client.request<AdsPreviewResponse>(
      `/api/integrations/ads/${encodeURIComponent(platform)}/preview`,
      { method: "POST", body },
    );
  }
}

export class TrendsAGI {
  readonly apiKey: string;
  readonly baseUrl: string;
  readonly authScheme: "bearer" | "x-api-key";
  readonly trends: TrendsNamespace;
  readonly insights: InsightsNamespace;
  readonly recommendations: RecommendationsNamespace;
  readonly ads: AdsNamespace;
  readonly credits: CreditsNamespace;

  private readonly fetchImpl: typeof fetch;
  private readonly defaultHeaders?: Record<string, string>;

  constructor(options: TrendsAGIOptions = {}) {
    const apiKey = (options.apiKey ?? readEnv("TRENDSAGI_API_KEY"))?.trim();
    if (!apiKey) {
      throw new TrendsAGIError(
        "No TrendsAGI API key found. Pass `apiKey` or set the TRENDSAGI_API_KEY environment variable.",
        { code: "MISSING_API_KEY" },
      );
    }
    const fetchImpl = options.fetch ?? globalThis.fetch?.bind(globalThis);
    if (!fetchImpl) {
      throw new TrendsAGIError(
        "No fetch implementation available. Use Node.js 18+ or pass a custom `fetch`.",
        { code: "MISSING_FETCH" },
      );
    }

    this.apiKey = apiKey;
    this.baseUrl = normalizeBaseUrl(options.baseUrl ?? readEnv("TRENDSAGI_BASE_URL") ?? DEFAULT_BASE_URL);
    this.authScheme = options.authScheme ?? "bearer";
    this.fetchImpl = fetchImpl;
    this.defaultHeaders = options.headers;

    this.trends = new TrendsNamespace(this);
    this.insights = new InsightsNamespace(this);
    this.recommendations = new RecommendationsNamespace(this);
    this.ads = new AdsNamespace(this);
    this.credits = new CreditsNamespace(this);
  }

  /**
   * Low-level request helper. Paths may be relative to `baseUrl` or absolute.
   */
  async request<T>(path: string, init: RequestOptions = {}): Promise<T> {
    const { method = "GET", body, query, headers: requestHeaders, ...rest } = init;
    const headers = new Headers(this.defaultHeaders);
    if (requestHeaders) {
      new Headers(requestHeaders).forEach((value, key) => headers.set(key, value));
    }
    if (!headers.has("accept")) headers.set("accept", "application/json");
    if (!headers.has("user-agent")) headers.set("user-agent", USER_AGENT);

    const hasJsonBody = body !== undefined && typeof body !== "string";
    if (hasJsonBody && !headers.has("content-type")) headers.set("content-type", "application/json");
    const requestBody =
      body === undefined ? undefined : typeof body === "string" ? body : JSON.stringify(body);

    if (!headers.has("authorization") && !headers.has("x-api-key")) {
      if (this.authScheme === "x-api-key") headers.set("x-api-key", this.apiKey);
      else headers.set("authorization", `Bearer ${this.apiKey}`);
    }

    const url = buildUrl(this.baseUrl, path, query);
    let response: Response;
    try {
      response = await this.fetchImpl(url, {
        ...rest,
        method,
        headers,
        body: requestBody,
      });
    } catch (error) {
      if (isAbortError(error)) throw error;
      const message = error instanceof Error ? error.message : String(error);
      throw new TrendsAGIError(`Network error while calling TrendsAGI: ${message}`, { cause: error });
    }

    if (!response.ok) {
      const text = await response.text().catch(() => "");
      let payload: unknown = text;
      if (text) {
        try {
          payload = JSON.parse(text);
        } catch {
          payload = text;
        }
      }
      const detail =
        extractDetail(payload) ||
        response.statusText ||
        `TrendsAGI request failed with status ${response.status}`;
      throw new TrendsAGIError(
        `TrendsAGI request failed with status ${response.status}: ${detail}`,
        {
          status: response.status,
          detail,
          body: payload,
          headers: response.headers,
        },
      );
    }

    if (response.status === 204) return undefined as T;

    const text = await response.text();
    if (!text) return undefined as T;
    if (isJsonContentType(response.headers.get("content-type"))) {
      return JSON.parse(text) as T;
    }
    try {
      return JSON.parse(text) as T;
    } catch {
      return text as unknown as T;
    }
  }
}
