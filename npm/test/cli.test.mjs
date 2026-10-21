import { test, before, after, beforeEach } from "node:test";
import assert from "node:assert/strict";
import { createServer } from "node:http";
import { spawn } from "node:child_process";
import { mkdtempSync, readFileSync, writeFileSync, statSync, existsSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const BIN = join(here, "..", "bin", "trendsagi.js");
const KEY = "ltc_live_testkey";

let server;
let baseURL;
let calls;
let routes;
let configDir;

before(async () => {
  server = createServer((req, res) => {
    let raw = "";
    req.on("data", (chunk) => (raw += chunk));
    req.on("end", () => {
      const url = new URL(req.url, "http://x");
      calls.push({
        method: req.method,
        path: url.pathname,
        query: Object.fromEntries(url.searchParams),
        body: raw ? JSON.parse(raw) : null,
        headers: req.headers,
      });
      let [status, payload, type] = routes[`${req.method} ${url.pathname}`] || [200, { ok: true }, "application/json"];
      if (typeof payload === "function") payload = payload();
      const body = Buffer.isBuffer(payload) ? payload : Buffer.from(JSON.stringify(payload));
      res.writeHead(status, { "Content-Type": type, "Content-Length": body.length });
      res.end(body);
    });
  });
  await new Promise((resolve) => server.listen(0, "127.0.0.1", resolve));
  baseURL = `http://127.0.0.1:${server.address().port}`;
});

after(() => server.close());

beforeEach(() => {
  calls = [];
  routes = {};
  configDir = mkdtempSync(join(tmpdir(), "trendsagi-cli-"));
});

function run(args, { env = {}, input } = {}) {
  return new Promise((resolve) => {
    const child = spawn(process.execPath, [BIN, ...args], {
      env: {
        PATH: process.env.PATH,
        HOME: configDir,
        TRENDSAGI_BASE_URL: baseURL,
        TRENDSAGI_CONFIG: join(configDir, "config.json"),
        TRENDSAGI_POLL_MS: "0",
        ...env,
      },
    });
    let stdout = "";
    let stderr = "";
    child.stdout.on("data", (d) => (stdout += d));
    child.stderr.on("data", (d) => (stderr += d));
    child.on("close", (code) => resolve({ code, stdout, stderr }));
    child.stdin.end(input ?? "");
  });
}

const withKey = { env: { TRENDSAGI_API_KEY: KEY } };

test("the npm package ships the same spec as the Python package", () => {
  const python = join(here, "..", "..", "src", "trendsagi", "cli_spec.json");
  if (!existsSync(python)) return; // installed from the registry, not the repository
  assert.deepEqual(JSON.parse(readFileSync(join(here, "..", "cli_spec.json"), "utf8")), JSON.parse(readFileSync(python, "utf8")));
});

test("trends list sends the query, key and CLI user agent", async () => {
  routes["GET /api/trends"] = [200, { trends: [{ id: 7, name: "AI chips" }] }, "application/json"];
  const { code, stdout } = await run(["trends", "list", "--category", "Technology", "--sort", "velocity", "--watchlist"], withKey);
  assert.equal(code, 0);
  assert.equal(JSON.parse(stdout).trends[0].id, 7);
  assert.deepEqual(calls[0].query, { category: "Technology", sort_by: "velocity", limit: "20", for_user_interests: "true" });
  assert.equal(calls[0].headers["x-api-key"], KEY);
  assert.match(calls[0].headers["user-agent"], /^trendsagi-cli\/\S+ node\//);
});

test("not logged in exits 4 without a request", async () => {
  const { code, stderr } = await run(["trends", "list"]);
  assert.equal(code, 4);
  assert.match(stderr, /trendsagi login/);
  assert.equal(calls.length, 0);
});

test("public commands skip the API key", async () => {
  assert.equal((await run(["status"])).code, 0);
  await run(["tools", "list"], withKey);
  assert.deepEqual(calls.map((c) => c.path), ["/status", "/api/agent/tools"]);
  assert.ok(calls.every((c) => !("x-api-key" in c.headers)));
});

test("login validates and saves the key privately; logout forgets it", async () => {
  routes["GET /api/user/profile"] = [200, { email: "ana@example.com" }, "application/json"];
  const { code, stderr } = await run(["login", "--with-token"], { input: `${KEY}\n` });
  assert.equal(code, 0, stderr);
  assert.match(stderr, /ana@example.com/);
  const path = join(configDir, "config.json");
  assert.equal(JSON.parse(readFileSync(path, "utf8")).api_key, KEY);
  if (process.platform !== "win32") assert.equal(statSync(path).mode & 0o777, 0o600);

  await run(["usage"]);
  assert.equal(calls.at(-1).headers["x-api-key"], KEY);
  assert.equal((await run(["logout"])).code, 0);
  assert.equal(JSON.parse(readFileSync(path, "utf8")).api_key, undefined);
});

test("login rejects text that is not an API key", async () => {
  const { code, stderr } = await run(["login", "--with-token"], { input: "hunter2\n" });
  assert.equal(code, 2);
  assert.match(stderr, /ltc_live_/);
  assert.equal(calls.length, 0);
});

test("flag beats env beats saved key", async () => {
  writeFileSync(join(configDir, "config.json"), JSON.stringify({ api_key: "ltc_live_saved" }));
  await run(["usage"]);
  await run(["usage"], { env: { TRENDSAGI_API_KEY: "ltc_live_env" } });
  await run(["--api-key", "ltc_live_flag", "usage"], { env: { TRENDSAGI_API_KEY: "ltc_live_env" } });
  await run(["usage", "--api-key=ltc_live_flag2"]);
  assert.deepEqual(calls.map((c) => c.headers["x-api-key"]), ["ltc_live_saved", "ltc_live_env", "ltc_live_flag", "ltc_live_flag2"]);
});

test("destructive commands need --yes without a terminal", async () => {
  const refused = await run(["webhooks", "delete", "5"], withKey);
  assert.equal(refused.code, 2);
  assert.match(refused.stderr, /--yes/);
  assert.equal(calls.length, 0);

  routes["DELETE /api/integrations/webhooks/5"] = [204, Buffer.alloc(0), "application/json"];
  assert.equal((await run(["webhooks", "delete", "5", "--yes"], withKey)).code, 0);
  assert.equal(calls[0].method, "DELETE");
});

test("ads apply builds the body and names the platform when asking", async () => {
  const refused = await run(["ads", "apply", "meta_ads", "--trend", "9", "--level", "ad"], withKey);
  assert.equal(refused.code, 2);
  assert.match(refused.stderr, /meta_ads/);
  await run(["-y", "ads", "apply", "meta_ads", "--trend", "9", "--level", "ad", "--strict-safety", "false"], withKey);
  assert.equal(calls[0].path, "/api/integrations/ads/meta_ads/apply");
  assert.deepEqual(calls[0].body, { trend_id: 9, apply_level: "ad", strict_safety: false });
});

test("nested body fields merge over --data", async () => {
  await run(
    ["ads", "report", "tiktok_ads", "--level", "campaign", "--start", "2026-10-01", "--end", "2026-10-07", "--account", "acc1",
      "--fields", "spend, clicks", "--data", '{"template_id": "custom", "level": "ad"}'],
    withKey,
  );
  assert.deepEqual(calls[0].body, {
    template_id: "custom",
    level: "campaign",
    platform: "tiktok_ads",
    date_range: { start_date: "2026-10-01", end_date: "2026-10-07" },
    scope: { account_id: "acc1" },
    fields: ["spend", "clicks"],
  });
});

test("watchlist add needs a keyword or a category", async () => {
  assert.equal((await run(["watchlist", "add"], withKey)).code, 2);
  await run(["watchlist", "add", "--category", "Beauty", "--repeat", "--growth", "25"], withKey);
  assert.deepEqual(calls[0].body, { category: "Beauty", alert_behavior: "notify_repeating", percentage_growth_value: 25 });
});

test("bad values are usage errors", async () => {
  assert.equal((await run(["trends", "get", "abc"], withKey)).code, 2);
  assert.equal((await run(["trends", "list", "--sort", "random"], withKey)).code, 2);
  assert.equal((await run(["trends", "list", "--nope"], withKey)).code, 2);
  assert.equal((await run(["trendz"], withKey)).code, 2);
  assert.equal(calls.length, 0);
});

test("sql refusal prints the code and hint", async () => {
  routes["POST /api/agent/sql"] = [400, { error: "unknown_table", detail: "saas_users is not available", hint: "See trendsagi schema." }, "application/json"];
  const { code, stderr } = await run(["sql", "SELECT * FROM saas_users"], withKey);
  assert.equal(code, 1);
  assert.match(stderr, /unknown_table/);
  assert.match(stderr, /See trendsagi schema\./);
  assert.deepEqual(calls[0].body, { query: "SELECT * FROM saas_users" });
});

test("tools call unwraps the text result", async () => {
  routes["POST /api/agent/tools/list_trends"] = [200, { content: [{ type: "text", text: '{"trends": [1]}' }], isError: false }, "application/json"];
  const ok = await run(["tools", "call", "list_trends", "--args", '{"limit": 5}', "-a", "category=Tech", "-a", "offset=10"], withKey);
  assert.equal(ok.code, 0);
  assert.deepEqual(JSON.parse(ok.stdout), { trends: [1] });
  assert.deepEqual(calls[0].body, { limit: 5, category: "Tech", offset: 10 });

  routes["POST /api/agent/tools/list_trends"] = [200, { content: [{ type: "text", text: '{"error": "http_403"}' }], isError: true }, "application/json"];
  const failed = await run(["tools", "call", "list_trends"], withKey);
  assert.equal(failed.code, 1);
  assert.match(failed.stderr, /http_403/);
});

test("api builds any request", async () => {
  await run(["api", "/api/trends", "-q", "limit=2"], withKey);
  await run(["api", "api/user/interests", "-f", "keyword=solar", "-f", "volume_threshold_value=500"], withKey);
  await run(["api", "/api/user/interests/3", "-X", "delete"], withKey);
  assert.deepEqual(calls.map((c) => [c.method, c.path]), [["GET", "/api/trends"], ["POST", "/api/user/interests"], ["DELETE", "/api/user/interests/3"]]);
  assert.deepEqual(calls[0].query, { limit: "2" });
  assert.deepEqual(calls[1].body, { keyword: "solar", volume_threshold_value: 500 });
});

test("report-export writes the raw CSV", async () => {
  routes["POST /api/integrations/ads/reporting/export"] = [200, Buffer.from("date,spend\n2026-10-01,5\n"), "text/csv"];
  const target = join(configDir, "report.csv");
  const { code } = await run(
    ["ads", "report-export", "google_ads", "--level", "ad", "--start", "2026-10-01", "--end", "2026-10-02", "--account", "1", "-o", target],
    withKey,
  );
  assert.equal(code, 0);
  assert.equal(readFileSync(target, "utf8"), "date,spend\n2026-10-01,5\n");
  assert.equal(calls[0].body.out, undefined);
});

test("insights generate --wait polls, then prints the insights", async () => {
  const states = ["PROCESSING", "SUCCESS"];
  routes["POST /api/trends/12/ai-insights/generate"] = [200, { task_id: "t1", status: "queued" }, "application/json"];
  routes["GET /api/trends/ai-insights/status/t1"] = [200, () => ({ status: states.shift() }), "application/json"];
  routes["GET /api/trends/12/ai-insights"] = [200, { trend_id: 12 }, "application/json"];
  const { code, stdout } = await run(["insights", "generate", "12", "--wait", "--force-refresh"], withKey);
  assert.equal(code, 0);
  assert.equal(JSON.parse(stdout).trend_id, 12);
  assert.deepEqual(calls[0].body, { force_refresh: true });
  assert.deepEqual(calls.slice(1).map((c) => c.path), ["/api/trends/ai-insights/status/t1", "/api/trends/ai-insights/status/t1", "/api/trends/12/ai-insights"]);
});

test("an invalid key exits 4", async () => {
  routes["GET /api/user/api-usage"] = [401, { detail: "Invalid or expired API key" }, "application/json"];
  const { code, stderr } = await run(["usage"], withKey);
  assert.equal(code, 4);
  assert.match(stderr, /Invalid or expired API key/);
});
