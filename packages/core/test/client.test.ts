import { afterEach, describe, expect, it, vi } from "vitest";
import { buildQueryString, TrendsAGI, TrendsAGIError } from "../src/index.js";

type Call = { url: string; init: RequestInit };

function jsonFetch(payload: unknown, status = 200, headers: Record<string, string> = {}) {
  const calls: Call[] = [];
  const fetchImpl = (async (input: string | URL | Request, init?: RequestInit) => {
    calls.push({ url: String(input), init: init ?? {} });
    return new Response(JSON.stringify(payload), {
      status,
      headers: { "content-type": "application/json", ...headers },
    });
  }) as typeof fetch;
  return { calls, fetchImpl };
}

function client(fetchImpl: typeof fetch, options: Record<string, unknown> = {}) {
  return new TrendsAGI({ apiKey: "test-key", fetch: fetchImpl, ...options });
}

afterEach(() => {
  vi.unstubAllEnvs();
  vi.useRealTimers();
});

describe("query serialization", () => {
  it("omits empty values and joins arrays with commas", () => {
    expect(
      buildQueryString({
        category: "Technology",
        limit: 5,
        missing: undefined,
        empty: null,
        interests: ["ai", "chips"],
        flag: false,
      }),
    ).toBe("?category=Technology&limit=5&interests=ai%2Cchips&flag=false");
  });

  it("returns an empty string when there is nothing to send", () => {
    expect(buildQueryString({ a: undefined, b: [], c: null })).toBe("");
    expect(buildQueryString()).toBe("");
  });

  it("serializes Date values as ISO strings", () => {
    const date = new Date("2026-01-02T03:04:05.000Z");
    expect(buildQueryString({ start_date: date })).toBe(
      "?start_date=2026-01-02T03%3A04%3A05.000Z",
    );
  });
});

describe("auth and headers", () => {
  it("sends Authorization: Bearer by default", async () => {
    const { calls, fetchImpl } = jsonFetch({ trends: [] });
    await client(fetchImpl).trends.list();
    const headers = new Headers(calls[0].init.headers);
    expect(headers.get("authorization")).toBe("Bearer test-key");
    expect(headers.get("accept")).toBe("application/json");
    expect(headers.get("user-agent")).toBe("@trendsagi/core");
  });

  it("supports X-API-Key authentication", async () => {
    const { calls, fetchImpl } = jsonFetch({ providers: [] });
    await client(fetchImpl, { authScheme: "x-api-key" }).ads.providers();
    const headers = new Headers(calls[0].init.headers);
    expect(headers.get("x-api-key")).toBe("test-key");
    expect(headers.get("authorization")).toBeNull();
  });

  it("merges default and per-request headers", async () => {
    const { calls, fetchImpl } = jsonFetch({ trends: [] });
    const trendsagi = client(fetchImpl, { headers: { "x-default": "1" } });
    await trendsagi.request("/api/trends", { headers: { "x-request": "2" } });
    const headers = new Headers(calls[0].init.headers);
    expect(headers.get("x-default")).toBe("1");
    expect(headers.get("x-request")).toBe("2");
  });

  it("reads TRENDSAGI_API_KEY and TRENDSAGI_BASE_URL from the environment", async () => {
    vi.stubEnv("TRENDSAGI_API_KEY", "env-key");
    vi.stubEnv("TRENDSAGI_BASE_URL", "https://example.test/");
    const { calls, fetchImpl } = jsonFetch({ trends: [] });
    const trendsagi = new TrendsAGI({ fetch: fetchImpl });
    expect(trendsagi.apiKey).toBe("env-key");
    await trendsagi.trends.list();
    expect(calls[0].url).toBe("https://example.test/api/trends");
  });

  it("throws a typed error without an API key", () => {
    vi.stubEnv("TRENDSAGI_API_KEY", "");
    expect(() => new TrendsAGI({ fetch: (() => {}) as unknown as typeof fetch })).toThrowError(
      TrendsAGIError,
    );
  });
});

describe("URL building", () => {
  it("joins the base URL and serializes list params", async () => {
    const { calls, fetchImpl } = jsonFetch({ trends: [] });
    await client(fetchImpl).trends.list({ category: "Beauty", limit: 5, sort_by: "velocity" });
    expect(calls[0].url).toBe(
      "https://api.trendsagi.com/api/trends?category=Beauty&limit=5&sort_by=velocity",
    );
  });

  it("encodes path segments", async () => {
    const { calls, fetchImpl } = jsonFetch({ providers: [] });
    await client(fetchImpl).ads.resources("google_ads", { account_id: "a b" });
    expect(calls[0].url).toBe(
      "https://api.trendsagi.com/api/integrations/ads/google_ads/resources?account_id=a+b",
    );
  });

  it("accepts absolute URLs", async () => {
    const { calls, fetchImpl } = jsonFetch({ ok: true });
    await client(fetchImpl).request("https://other.test/api/x", { query: { a: 1 } });
    expect(calls[0].url).toBe("https://other.test/api/x?a=1");
  });
});

describe("namespaces", () => {
  it("maps trend methods to their endpoints", async () => {
    const { calls, fetchImpl } = jsonFetch({ trends: [], data: [] });
    const trendsagi = client(fetchImpl);
    await trendsagi.trends.get(12);
    await trendsagi.trends.analytics(12, { period: "7d" });
    await trendsagi.trends.categories();
    await trendsagi.trends.autocomplete("skin");
    await trendsagi.insights.get(12);
    await trendsagi.insights.search({ q: "skin", limit: 3 });
    await trendsagi.recommendations.list({ priority: "high" });
    expect(calls.map((call) => call.url)).toEqual([
      "https://api.trendsagi.com/api/trends/12",
      "https://api.trendsagi.com/api/trends/12/analytics?period=7d",
      "https://api.trendsagi.com/api/trends/categories",
      "https://api.trendsagi.com/api/trends/autocomplete?q=skin",
      "https://api.trendsagi.com/api/trends/12/ai-insights",
      "https://api.trendsagi.com/api/insights/search?q=skin&limit=3",
      "https://api.trendsagi.com/api/intelligence/recommendations?priority=high",
    ]);
  });

  it("normalizes category and autocomplete arrays", async () => {
    let payload: unknown = ["Technology", "Beauty"];
    const fetchImpl = (async () =>
      new Response(JSON.stringify(payload), {
        headers: { "content-type": "application/json" },
      })) as typeof fetch;
    const trendsagi = client(fetchImpl);
    const categories = await trendsagi.trends.categories();
    expect(categories.categories).toEqual(["Technology", "Beauty"]);
    payload = ["skin care", "skin barrier"];
    const autocomplete = await trendsagi.trends.autocomplete("skin");
    expect(autocomplete.results).toEqual([{ name: "skin care" }, { name: "skin barrier" }]);
    expect(autocomplete.suggestions).toEqual(["skin care", "skin barrier"]);
  });

  it("posts ads previews as JSON", async () => {
    const { calls, fetchImpl } = jsonFetch({ blocked: false });
    await client(fetchImpl).ads.preview("meta_ads", { trend_id: 7, apply_level: "ad_set" });
    expect(calls[0].url).toBe("https://api.trendsagi.com/api/integrations/ads/meta_ads/preview");
    expect(calls[0].init.method).toBe("POST");
    expect(new Headers(calls[0].init.headers).get("content-type")).toBe("application/json");
    expect(JSON.parse(String(calls[0].init.body))).toEqual({
      trend_id: 7,
      apply_level: "ad_set",
    });
  });
});

describe("errors", () => {
  it("throws a typed 401 error with detail and body", async () => {
    const { fetchImpl } = jsonFetch({ detail: "Invalid API key" }, 401);
    const error = await client(fetchImpl)
      .trends.list()
      .catch((caught: unknown) => caught);
    expect(error).toBeInstanceOf(TrendsAGIError);
    const typed = error as TrendsAGIError;
    expect(typed.status).toBe(401);
    expect(typed.detail).toBe("Invalid API key");
    expect(typed.body).toEqual({ detail: "Invalid API key" });
    expect(typed.message).toContain("401");
  });

  it("exposes 429 status and Retry-After headers", async () => {
    const { fetchImpl } = jsonFetch({ error: "Rate limit exceeded" }, 429, {
      "retry-after": "30",
    });
    const error = (await client(fetchImpl)
      .trends.list()
      .catch((caught: unknown) => caught)) as TrendsAGIError;
    expect(error.status).toBe(429);
    expect(error.detail).toBe("Rate limit exceeded");
    expect(error.headers?.get("retry-after")).toBe("30");
  });

  it("falls back to raw text for non-JSON errors", async () => {
    const fetchImpl = (async () =>
      new Response("Bad gateway", { status: 502 })) as typeof fetch;
    const error = (await client(fetchImpl)
      .trends.list()
      .catch((caught: unknown) => caught)) as TrendsAGIError;
    expect(error.status).toBe(502);
    expect(error.detail).toBe("Bad gateway");
  });

  it("wraps network failures", async () => {
    const fetchImpl = (async () => {
      throw new Error("socket hang up");
    }) as typeof fetch;
    const error = (await client(fetchImpl)
      .trends.list()
      .catch((caught: unknown) => caught)) as TrendsAGIError;
    expect(error).toBeInstanceOf(TrendsAGIError);
    expect(error.message).toContain("socket hang up");
    expect(error.cause).toBeInstanceOf(Error);
  });

  it("rethrows abort errors unchanged", async () => {
    const controller = new AbortController();
    const fetchImpl = (async () => {
      controller.abort();
      throw new DOMException("This operation was aborted", "AbortError");
    }) as typeof fetch;
    const error = await client(fetchImpl)
      .trends.list({ signal: controller.signal })
      .catch((caught: unknown) => caught);
    expect(error).toBeInstanceOf(DOMException);
    expect((error as Error).name).toBe("AbortError");
  });

  it("passes the abort signal to fetch", async () => {
    const { calls, fetchImpl } = jsonFetch({ trends: [] });
    const controller = new AbortController();
    await client(fetchImpl).trends.list({ signal: controller.signal });
    expect(calls[0].init.signal).toBe(controller.signal);
  });
});

describe("responses", () => {
  it("returns undefined for 204", async () => {
    const fetchImpl = (async () => new Response(null, { status: 204 })) as typeof fetch;
    await expect(client(fetchImpl).request("/api/empty")).resolves.toBeUndefined();
  });

  it("returns text for non-JSON success bodies", async () => {
    const fetchImpl = (async () =>
      new Response("ok", { headers: { "content-type": "text/plain" } })) as typeof fetch;
    await expect(client(fetchImpl).request("/api/health")).resolves.toBe("ok");
  });

  it("returns parsed JSON for JSON success bodies", async () => {
    const { fetchImpl } = jsonFetch({ trends: [{ name: "#AIUpdate" }] });
    await expect(client(fetchImpl).trends.list()).resolves.toEqual({
      trends: [{ name: "#AIUpdate" }],
    });
  });
});
