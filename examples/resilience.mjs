// Run in Node.js. Keep credentials server-side.
export async function fetchResilience({apiKey, baseURL = "https://api.trendsagi.com", fetchImpl = fetch}) {
 if (!apiKey) throw new Error("TRENDSAGI_API_KEY is required");
 const get = async path => {
  const response = await fetchImpl(new URL(path, baseURL), {
   headers: {"X-API-Key": apiKey, Accept: "application/json"},
   signal: AbortSignal.timeout(20000),
  });
  if (!response.ok) throw new Error("TrendsAGI HTTP " + response.status);
  return response.json();
 };
 const list = await get("/api/intelligence/crisis-events?status=all&period=7d&limit=10");
 if (!list.events.length) return null;
 return get("/api/intelligence/crisis-events/" + encodeURIComponent(list.events[0].id) + "/evidence");
}
