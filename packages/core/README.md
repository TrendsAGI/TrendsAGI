# `@trendsagi/core`

Typed JavaScript/TypeScript client for the [TrendsAGI](https://trendsagi.com) REST API. Live trend volume, velocity and growth, AI insights, recommendations and ads previews, with no runtime dependencies.

- Node.js 18+ (ESM or CommonJS), Bun, Deno, Cloudflare Workers and modern browsers
- Injectable `fetch` for tests and edge runtimes
- Typed errors, `AbortSignal` support and full TypeScript declarations

```bash
npm install @trendsagi/core
```

## Quickstart

```ts
import { TrendsAGI } from "@trendsagi/core";

// Reads TRENDSAGI_API_KEY
const trendsagi = new TrendsAGI();

const { trends } = await trendsagi.trends.list({
  category: "Technology",
  limit: 5,
});

console.log(trends.map((trend) => trend.name));
```

Get an API key from your TrendsAGI profile (**Profile → API Keys**).

## Configuration

```ts
const trendsagi = new TrendsAGI({
  apiKey: "sk_live_...",          // default: TRENDSAGI_API_KEY
  baseUrl: "https://api.trendsagi.com", // default: TRENDSAGI_BASE_URL
  headers: { "x-trace-id": "..." },    // merged into every request
  authScheme: "bearer",          // or "x-api-key"
  fetch: customFetch,            // default: globalThis.fetch
});
```

`TRENDSAGI_API_KEY` is read at construction. Construction throws
`TrendsAGIError` with `code: "MISSING_API_KEY"` when no key is available.

## Namespaces

```ts
// Trends
await trendsagi.trends.list({ category: "Technology", sort_by: "velocity", limit: 10 });
await trendsagi.trends.get(123);
await trendsagi.trends.analytics(123, { period: "7d" });
await trendsagi.trends.categories();
await trendsagi.trends.autocomplete("skin");
await trendsagi.trends.dossier(123);
await trendsagi.trends.discoveries({ limit: 20 });
await trendsagi.trends.enrich(123, { modules: ["search_demand"], region: "US" });
await trendsagi.trends.searchDemand(123, { geo: "US" });
await trendsagi.trends.brandMomentum(123, { window: "7d" });
await trendsagi.trends.creators(123);
await trendsagi.trends.ask(123, "What should we do next?");
await trendsagi.trends.socialEvidence(123);
await trendsagi.trends.runSocialEvidence(123, { modules: ["posts"] });

// Credits
await trendsagi.credits.socialEvidence();
await trendsagi.credits.buySocialEvidence("social_evidence_10");

// AI insights (read-only cached result)
await trendsagi.insights.get(123);
await trendsagi.insights.search({ q: "skincare", limit: 10 });

// Recommendations
await trendsagi.recommendations.list({ priority: "high", status: "new" });

// Ads
await trendsagi.ads.providers();
await trendsagi.ads.resources("google_ads", { account_id: "123-456-7890" });
await trendsagi.ads.preview("google_ads", {
  trend_id: 123,
  apply_level: "ad_group",
  ad_group_id: "2345678",
});
```

`ads.preview` only previews changes. Applying them is an account action in the
TrendsAGI app, not part of this client.

## Long-tail endpoints

```ts
const report = await trendsagi.request<{ rows: unknown[] }>("/api/some/endpoint", {
  query: { lookback_hours: 24 },
});
```

## Errors

```ts
import { TrendsAGI, TrendsAGIError } from "@trendsagi/core";

try {
  await trendsagi.trends.get(1);
} catch (error) {
  if (error instanceof TrendsAGIError) {
    console.error(error.status, error.detail, error.body);
  }
}
```

Non-2xx responses throw `TrendsAGIError` with `status`, `detail`, `body` and
`headers`. Abort errors (`AbortError`) are rethrown unchanged.

## Cancellation

```ts
const controller = new AbortController();
const promise = trendsagi.trends.list({ category: "Beauty", signal: controller.signal });
controller.abort();
```

## Query serialization

`undefined`, `null` and empty arrays are omitted. Arrays are serialized
comma-separated (`interests=a,b`), and `Date` values become ISO strings.

## Types

Every response shape is exported from the package root. The repository also
checks in `packages/core/src/schema.d.ts`, generated from the TrendsAGI
OpenAPI document by `npm run codegen`; consumers never need to run codegen.

`request<T>` stays generic for endpoints that are not modelled yet.

## License

MIT © TrendsAGI. This package is an official TrendsAGI package. It is not
affiliated with OpenAI, Anthropic, LangChain or Vercel.
