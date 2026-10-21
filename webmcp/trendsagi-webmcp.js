// Offers TrendsAGI's tools to the AI agent built into the visitor's browser,
// through WebMCP (https://webmachinelearning.github.io/webmcp/).
//
// The page never holds your TrendsAGI API key. It lists and runs the tools
// through routes on your own server (see server.py), which keeps the key and
// checks that the visitor is signed in to your site.
//
//   import { registerTrendsAGITools } from "./trendsagi-webmcp.js";
//
//   const unregister = await registerTrendsAGITools({ endpoint: "/trendsagi/tools" });
//   // When the tools stop applying, for example on sign-out:
//   unregister();

export async function registerTrendsAGITools({ endpoint = "/trendsagi/tools" } = {}) {
  // The current draft exposes WebMCP on document; earlier drafts and
  // polyfills used navigator.
  const modelContext = globalThis.document?.modelContext ?? globalThis.navigator?.modelContext;
  if (typeof modelContext?.registerTool !== "function") return () => {};

  const response = await fetch(endpoint, { credentials: "same-origin" });
  if (!response.ok) throw new Error(`TrendsAGI tools: ${endpoint} answered HTTP ${response.status}`);
  const tools = await response.json();

  const controller = new AbortController();
  for (const tool of tools) {
    try {
      await modelContext.registerTool(
        {
          ...tool,
          async execute(input) {
            // Older Chrome builds pass the arguments as JSON text.
            const args = typeof input === "string" ? JSON.parse(input || "{}") : input ?? {};
            const result = await fetch(`${endpoint}/${encodeURIComponent(tool.name)}`, {
              method: "POST",
              credentials: "same-origin",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify(args),
            });
            if (!result.ok) {
              return JSON.stringify({ error: `http_${result.status}`, detail: "The tool call was refused; check that the user is signed in." });
            }
            // {"result": ...} on success, {"error": ..., "detail": ...} otherwise.
            return JSON.stringify(await result.json());
          },
        },
        { signal: controller.signal },
      );
    } catch {
      // A name already registered by another script, or a frame without
      // permission: skip that tool and keep the rest.
    }
  }
  // Aborting the signal is how WebMCP unregisters tools.
  return () => controller.abort();
}
