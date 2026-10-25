import { TrendsAGI } from "@trendsagi/core";

const hasKey = Boolean(process.env.TRENDSAGI_API_KEY);

const mockFetch = async (input) => {
  const url = new URL(String(input));
  if (url.pathname === "/api/trends") {
    return new Response(
      JSON.stringify({
        trends: [
          {
            id: 1,
            name: "#AIUpdate",
            category: url.searchParams.get("category") ?? "Technology",
            volume: 55200,
          },
          {
            id: 2,
            name: "skin barrier repair",
            category: url.searchParams.get("category") ?? "Beauty",
            volume: 18400,
          },
        ],
        total: 2,
      }),
      { headers: { "content-type": "application/json" } },
    );
  }
  return new Response(JSON.stringify({ detail: "Not found in mock" }), {
    status: 404,
    headers: { "content-type": "application/json" },
  });
};

const trendsagi = hasKey
  ? new TrendsAGI()
  : new TrendsAGI({ apiKey: "mock-key", fetch: mockFetch });

if (!hasKey) {
  console.log("No TRENDSAGI_API_KEY set: using the mock fetch in this example.\n");
}

const { trends } = await trendsagi.trends.list({ category: "Technology", limit: 5 });
console.log(trends.map((trend) => trend.name));
