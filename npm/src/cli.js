// The trendsagi command line for Node.js.
//
// Every API command is declared in ../cli_spec.json, the same file the Python
// package (pip install trendsagi) reads, so both CLIs accept the same commands
// and flags. Commands that need more than one request or special output name a
// "handler" in the spec and are implemented below. No dependencies: Node 18+
// for fetch, Node 22+ (or 21 with --experimental-websocket) for `stream`.

import { readFileSync, writeFileSync, mkdirSync, renameSync, openSync, closeSync } from "node:fs";
import { homedir } from "node:os";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { createInterface } from "node:readline";

const here = dirname(fileURLToPath(import.meta.url));
export const SPEC = JSON.parse(readFileSync(join(here, "..", "cli_spec.json"), "utf8"));
const VERSION = JSON.parse(readFileSync(join(here, "..", "package.json"), "utf8")).version;

const DEFAULT_BASE_URL = "https://api.trendsagi.com";
const API_KEY_PREFIXES = ["ltc_live_", "ltc_test_"];
const BODY_METHODS = new Set(["POST", "PUT", "PATCH"]);
const EXIT_ERROR = 1;
const EXIT_USAGE = 2;
const EXIT_AUTH = 4;
const TASK_DONE = new Set(["SUCCESS", "COMPLETED", "DONE"]);
const TASK_FAILED = new Set(["FAILURE", "FAILED", "ERROR"]);
const USER_AGENT = `trendsagi-cli/${VERSION} node/${process.versions.node}`;

class CLIError extends Error {
  constructor(message, code = EXIT_ERROR) {
    super(message);
    this.code = code;
  }
}

class APIError extends Error {
  constructor(status, detail, body) {
    super(`Error ${status}: ${detail}`);
    this.status = status;
    this.detail = detail;
    this.body = body;
  }
}

// --- saved login --------------------------------------------------------------

export function configPath(env = process.env) {
  if (env.TRENDSAGI_CONFIG) return env.TRENDSAGI_CONFIG;
  const base =
    process.platform === "win32"
      ? env.APPDATA || join(homedir(), "AppData", "Roaming")
      : env.XDG_CONFIG_HOME || join(homedir(), ".config");
  return join(base, "trendsagi", "config.json");
}

function readConfig() {
  const path = configPath();
  let text;
  try {
    text = readFileSync(path, "utf8");
  } catch (error) {
    if (error.code === "ENOENT") return {};
    throw new CLIError(`Could not read ${path}: ${error.message}`);
  }
  try {
    const data = JSON.parse(text);
    return data && typeof data === "object" && !Array.isArray(data) ? data : {};
  } catch (error) {
    throw new CLIError(`Could not read ${path}: ${error.message}`);
  }
}

function writeConfig(data) {
  const path = configPath();
  mkdirSync(dirname(path), { recursive: true, mode: 0o700 });
  const tmp = `${path}.tmp`;
  closeSync(openSync(tmp, "w", 0o600));
  writeFileSync(tmp, JSON.stringify(data, null, 2) + "\n", { mode: 0o600 });
  renameSync(tmp, path);
  return path;
}

// --- argument parsing ------------------------------------------------------------

const GLOBAL_OPTIONS = [
  { flag: "api-key", help: "API key (default: $TRENDSAGI_API_KEY or the saved login)." },
  { flag: "base-url", help: `API base URL (default: ${DEFAULT_BASE_URL}).` },
  { flag: "json", type: "flag", help: "Print raw JSON instead of tables." },
  { flag: "yes", short: "y", type: "flag", help: "Do not ask before changing or deleting things." },
];

function parseBool(value) {
  const lowered = String(value).trim().toLowerCase();
  if (["true", "1", "yes", "on"].includes(lowered)) return true;
  if (["false", "0", "no", "off"].includes(lowered)) return false;
  throw new CLIError(`expected true or false, got '${value}'`, EXIT_USAGE);
}

function readStdin() {
  return readFileSync(0, "utf8");
}

function parseJSONArg(value) {
  let text = value;
  if (value === "-") text = readStdin();
  else if (value.startsWith("@")) {
    try {
      text = readFileSync(value.slice(1), "utf8");
    } catch (error) {
      throw new CLIError(`cannot read ${value.slice(1)}: ${error.message}`, EXIT_USAGE);
    }
  }
  try {
    return JSON.parse(text);
  } catch (error) {
    throw new CLIError(`invalid JSON: ${error.message}`, EXIT_USAGE);
  }
}

function jsonValue(raw) {
  try {
    return JSON.parse(raw);
  } catch {
    return raw;
  }
}

function convert(spec, value, label) {
  const type = spec.type || "string";
  let result = value;
  if (type === "int") {
    if (!/^-?\d+$/.test(value)) throw new CLIError(`${label}: expected a whole number, got '${value}'`, EXIT_USAGE);
    result = Number.parseInt(value, 10);
  } else if (type === "float") {
    result = Number(value);
    if (value.trim() === "" || Number.isNaN(result)) throw new CLIError(`${label}: expected a number, got '${value}'`, EXIT_USAGE);
  } else if (type === "bool") {
    result = parseBool(value);
  } else if (type === "json") {
    result = parseJSONArg(value);
  } else if (type === "list") {
    result = value.split(",").map((part) => part.trim()).filter(Boolean);
  } else if (type === "pairs") {
    const index = value.indexOf("=");
    if (index < 1) throw new CLIError(`${label}: expected KEY=VALUE, got '${value}'`, EXIT_USAGE);
    result = [value.slice(0, index), value.slice(index + 1)];
  }
  if (spec.choices && !spec.choices.includes(result)) {
    throw new CLIError(`${label}: choose from ${spec.choices.join(", ")} (got '${value}')`, EXIT_USAGE);
  }
  return result;
}

function findCommand(commands, name) {
  return commands.find((cmd) => cmd.name === name || (cmd.aliases || []).includes(name));
}

function dataOption(cmd) {
  return cmd.data ? [{ flag: "data", short: "d", type: "json", help: "Request body as JSON, @file.json or - for standard input; flags override its fields." }] : [];
}

/** Parse argv into { path: [command names], cmd, args, options, globals, help }. */
export function parse(argv) {
  const globals = {};
  const tokens = [];
  // Global options may appear anywhere.
  for (let i = 0; i < argv.length; i++) {
    const token = argv[i];
    const [name, inline] = token.startsWith("--") ? token.slice(2).split(/=(.*)/s) : [null];
    if (name === "api-key" || name === "base-url") {
      const value = inline ?? argv[++i];
      if (value === undefined) throw new CLIError(`--${name} needs a value`, EXIT_USAGE);
      globals[name] = value;
    } else if (token === "--json") globals.json = true;
    else if (token === "-y" || token === "--yes") globals.yes = true;
    else tokens.push(token);
  }

  const path = [];
  let commands = SPEC.commands;
  let cmd = null;
  let group = null;
  while (tokens.length && !tokens[0].startsWith("-")) {
    const found = findCommand(commands, tokens[0]);
    if (!found) break;
    tokens.shift();
    path.push(found.name);
    if (found.commands) {
      group = found;
      commands = found.commands;
    } else {
      cmd = found;
      break;
    }
  }
  if (tokens.includes("-h") || tokens.includes("--help")) return { path, cmd, group, globals, help: true };
  if (!cmd) {
    if (tokens.length && !tokens[0].startsWith("-")) {
      throw new CLIError(`Unknown command '${[...path, tokens[0]].join(" ")}'. Run 'trendsagi${path.length ? " " + path.join(" ") : ""} --help'.`, EXIT_USAGE);
    }
    if (tokens.includes("--version")) return { version: true };
    return { path, cmd, group, globals, help: true, bare: true };
  }

  const options = [...(cmd.options || []), ...dataOption(cmd)];
  const values = {};
  const positionals = [];
  for (let i = 0; i < tokens.length; i++) {
    const token = tokens[i];
    if (token === "--") {
      positionals.push(...tokens.slice(i + 1));
      break;
    }
    let spec = null;
    let inline;
    if (token.startsWith("--")) {
      const [name, rest] = token.slice(2).split(/=(.*)/s);
      spec = options.find((opt) => opt.flag === name);
      inline = rest;
      if (!spec) throw new CLIError(`Unknown option --${name} for 'trendsagi ${path.join(" ")}'.`, EXIT_USAGE);
    } else if (/^-[A-Za-z]$/.test(token)) {
      spec = options.find((opt) => opt.short === token.slice(1));
      if (!spec) throw new CLIError(`Unknown option ${token} for 'trendsagi ${path.join(" ")}'.`, EXIT_USAGE);
    }
    if (!spec) {
      positionals.push(token);
      continue;
    }
    const label = `--${spec.flag}`;
    if (spec.type === "flag") {
      values[spec.flag] = spec.value ?? true;
      continue;
    }
    const raw = inline ?? tokens[++i];
    if (raw === undefined) throw new CLIError(`${label} needs a value`, EXIT_USAGE);
    const value = convert(spec, raw, label);
    if (spec.type === "pairs") (values[spec.flag] ||= []).push(value);
    else values[spec.flag] = value;
  }

  const args = {};
  const argSpecs = cmd.args || [];
  argSpecs.forEach((spec, index) => {
    const raw = positionals[index];
    if (raw === undefined) {
      if (!spec.optional) throw new CLIError(`Missing ${spec.name}. Usage: ${usage(path, cmd)}`, EXIT_USAGE);
      return;
    }
    args[spec.name] = convert(spec, raw, spec.name);
  });
  if (positionals.length > argSpecs.length) {
    throw new CLIError(`Unexpected argument '${positionals[argSpecs.length]}'. Usage: ${usage(path, cmd)}`, EXIT_USAGE);
  }
  for (const opt of options) {
    if (values[opt.flag] === undefined && opt.default !== undefined) values[opt.flag] = opt.default;
    if (opt.required && values[opt.flag] === undefined) {
      throw new CLIError(`--${opt.flag} is required. Usage: ${usage(path, cmd)}`, EXIT_USAGE);
    }
  }
  return { path, cmd, args, options: values, globals };
}

// --- help ----------------------------------------------------------------------

function usage(path, cmd) {
  const parts = ["trendsagi", ...path];
  for (const arg of cmd.args || []) parts.push(arg.optional ? `[${arg.name}]` : `<${arg.name}>`);
  if ((cmd.options || []).length || cmd.data) parts.push("[options]");
  return parts.join(" ");
}

function wrapRows(rows) {
  const width = Math.min(Math.max(...rows.map(([left]) => left.length), 0), 28);
  return rows
    .map(([left, right]) => (left.length > width ? `  ${left}\n  ${" ".repeat(width)}  ${right}` : `  ${left.padEnd(width)}  ${right}`))
    .join("\n");
}

function optionLabel(opt) {
  const flag = `${opt.short ? `-${opt.short}, ` : ""}--${opt.flag}`;
  if (opt.type === "flag") return flag;
  const metavar = opt.choices ? `{${opt.choices.join(",")}}` : opt.metavar || { int: "N", float: "NUMBER", bool: "true|false", json: "JSON", list: "A,B", pairs: "KEY=VALUE" }[opt.type] || opt.flag.toUpperCase().replace(/-/g, "_");
  return `${flag} ${metavar}`;
}

function helpText({ path, cmd, group }) {
  if (cmd) {
    const lines = [`usage: ${usage(path, cmd)}`, "", cmd.help];
    if ((cmd.args || []).length) {
      lines.push("", "arguments:", wrapRows(cmd.args.map((a) => [a.name, `${a.help || ""}${a.choices ? ` One of: ${a.choices.join(", ")}.` : ""}`])));
    }
    const options = [...(cmd.options || []), ...dataOption(cmd)];
    if (options.length) {
      lines.push("", "options:", wrapRows(options.map((o) => [optionLabel(o), `${o.help || ""}${o.default !== undefined && !(o.help || "").includes("default") ? ` (default ${o.default})` : ""}`])));
    }
    lines.push("", "global options:", wrapRows(GLOBAL_OPTIONS.map((o) => [optionLabel(o), o.help])));
    return lines.join("\n");
  }
  const commands = group ? group.commands : SPEC.commands;
  const lines = [
    `usage: trendsagi ${path.length ? path.join(" ") + " " : ""}<command> [options]`,
    "",
    group ? group.help : SPEC.description,
    "",
    "commands:",
    wrapRows(commands.map((c) => [c.name + ((c.aliases || []).length ? ` (${c.aliases.join(", ")})` : ""), c.help])),
  ];
  if (!group) {
    lines.push(
      "",
      "global options:",
      wrapRows([...GLOBAL_OPTIONS.map((o) => [optionLabel(o), o.help]), ["--version", "Print the version."]]),
      "",
      "examples:",
      "  trendsagi login",
      "  trendsagi trends list --sort velocity --limit 10",
      "  trendsagi insights get 123",
      '  trendsagi sql "SELECT category, count(*) FROM trends GROUP BY 1"',
      "  trendsagi api /api/trends -q category=Technology",
      "",
      `Docs: ${SPEC.docs_url}`,
    );
  }
  return lines.join("\n");
}

// --- requests --------------------------------------------------------------------

function put(target, dotted, value) {
  const keys = dotted.split(".");
  for (const key of keys.slice(0, -1)) {
    if (typeof target[key] !== "object" || target[key] === null || Array.isArray(target[key])) target[key] = {};
    target = target[key];
  }
  target[keys[keys.length - 1]] = value;
}

function queryValue(value) {
  if (typeof value === "boolean") return value ? "true" : "false";
  if (Array.isArray(value)) return value.join(",");
  return String(value);
}

export function buildRequest(cmd, args, options) {
  const method = cmd.method;
  let path = cmd.path;
  const defaultIn = BODY_METHODS.has(method) ? "body" : "query";
  const query = {};
  const body = {};

  if (options.data !== undefined) {
    if (!options.data || typeof options.data !== "object" || Array.isArray(options.data)) {
      throw new CLIError("--data must be a JSON object.", EXIT_USAGE);
    }
    Object.assign(body, options.data);
  }

  const given = new Set();
  for (const arg of cmd.args || []) {
    let value = args[arg.name];
    if (value === undefined) continue;
    if (arg.stdin && value === "-") value = readStdin().trim();
    given.add(arg.name);
    const placeholder = `{${arg.name}}`;
    const where = arg.in || (path.includes(placeholder) ? "path" : defaultIn);
    if (where === "path") path = path.replace(placeholder, encodeURIComponent(String(value)));
    else put(where === "query" ? query : body, arg.param || arg.name, value);
  }
  for (const opt of cmd.options || []) {
    if (opt.local) continue;
    const value = options[opt.flag];
    if (value === undefined) continue;
    given.add(opt.flag);
    const where = opt.in || defaultIn;
    put(where === "query" ? query : body, opt.param || opt.flag.replace(/-/g, "_"), value);
  }
  if (cmd.require_one_of && !cmd.require_one_of.some((name) => given.has(name))) {
    throw new CLIError(`Give one of: ${cmd.require_one_of.join(", ")}.`, EXIT_USAGE);
  }
  for (const key of Object.keys(query)) query[key] = queryValue(query[key]);
  return { method, path, query, body: BODY_METHODS.has(method) ? body : undefined };
}

class Context {
  constructor(globals) {
    this.flagApiKey = globals["api-key"];
    this._config = undefined;
    if (this.flagApiKey) [this.apiKey, this.keySource] = [this.flagApiKey, "--api-key"];
    else if (process.env.TRENDSAGI_API_KEY) [this.apiKey, this.keySource] = [process.env.TRENDSAGI_API_KEY, "TRENDSAGI_API_KEY"];
    else {
      this.apiKey = this.config.api_key;
      this.keySource = this.apiKey ? configPath() : null;
    }
    this.baseURL = (globals["base-url"] || process.env.TRENDSAGI_BASE_URL || this.config.base_url || DEFAULT_BASE_URL).replace(/\/+$/, "");
    this.json = Boolean(globals.json);
    this.yes = Boolean(globals.yes);
    this.tty = Boolean(process.stdout.isTTY);
  }

  get config() {
    if (this._config === undefined) this._config = readConfig();
    return this._config;
  }

  requireKey(apiKey = this.apiKey) {
    if (!apiKey) {
      throw new CLIError(`Not logged in. Run 'trendsagi login' or set TRENDSAGI_API_KEY.\nCreate an API key at ${SPEC.api_keys_url}`, EXIT_AUTH);
    }
    return apiKey;
  }

  async request(method, path, { query, body, auth = true, raw = false, apiKey } = {}) {
    const url = new URL(this.baseURL + (path.startsWith("/") ? path : `/${path}`));
    for (const [key, value] of Object.entries(query || {})) url.searchParams.set(key, value);
    const headers = { Accept: "application/json", "User-Agent": USER_AGENT };
    if (auth) headers["X-API-Key"] = this.requireKey(apiKey || this.apiKey);
    if (body !== undefined) headers["Content-Type"] = "application/json";

    for (let attempt = 0; ; attempt++) {
      let response;
      try {
        response = await fetch(url, { method, headers, body: body === undefined ? undefined : JSON.stringify(body) });
      } catch (error) {
        throw new CLIError(`Network error communicating with API: ${error.cause?.message || error.message}`);
      }
      const content = Buffer.from(await response.arrayBuffer());
      if (response.ok) {
        if (raw) return content;
        if (response.status === 204 || content.length === 0) return null;
        try {
          return JSON.parse(content.toString("utf8"));
        } catch {
          return content.toString("utf8");
        }
      }
      if (response.status === 429 && attempt < 2) {
        const wait = Math.min(Number(response.headers.get("retry-after")) || 2 ** attempt, 10);
        await new Promise((resolve) => setTimeout(resolve, wait * 1000));
        continue;
      }
      let errorBody = null;
      try {
        errorBody = JSON.parse(content.toString("utf8"));
      } catch {}
      const text = content.toString("utf8").replace(/<[^>]+>/g, " ").replace(/\s+/g, " ").trim();
      const detail = errorBody && typeof errorBody === "object" && errorBody.detail !== undefined ? errorBody.detail : text;
      throw new APIError(response.status, typeof detail === "string" ? detail : JSON.stringify(detail), errorBody);
    }
  }
}

async function confirm(ctx, cmd, args) {
  if (!cmd.confirm || ctx.yes) return;
  const prompt = cmd.confirm.replace(/\{(\w+)\}/g, (_, name) => String(args[name] ?? ""));
  if (!process.stdin.isTTY) throw new CLIError(`${prompt} Pass --yes to confirm.`, EXIT_USAGE);
  const answer = await ask(`${prompt} [y/N] `);
  if (!["y", "yes"].includes(answer.trim().toLowerCase())) throw new CLIError("Cancelled.");
}

function ask(question, { hidden = false } = {}) {
  return new Promise((resolve) => {
    const rl = createInterface({ input: process.stdin, output: process.stderr, terminal: true });
    if (hidden) {
      rl._writeToOutput = (text) => {
        if (text.includes(question)) process.stderr.write(text);
      };
    }
    rl.question(question, (answer) => {
      rl.close();
      if (hidden) process.stderr.write("\n");
      resolve(answer);
    });
  });
}

// --- output ----------------------------------------------------------------------

const out = (text) => process.stdout.write(text + "\n");
const err = (text) => process.stderr.write(text + "\n");
const printJSON = (data) => out(JSON.stringify(data, null, 2));

function cell(value) {
  if (value === null || value === undefined) return "";
  if (typeof value === "boolean") return value ? "yes" : "no";
  if (typeof value === "number") return Number.isInteger(value) ? String(value) : String(Number(value.toFixed(2)));
  if (Array.isArray(value)) return value.map(cell).join(", ");
  if (typeof value === "object") return JSON.stringify(value);
  return String(value).split(/\s+/).filter(Boolean).join(" ");
}

const truncate = (text, width) => (text.length <= width ? text : text.slice(0, Math.max(width - 1, 0)) + "…");

export function renderTable(rows, columns = []) {
  if (!rows.length) return "No results.";
  let present = columns.filter((c) => rows.some((r) => r && typeof r === "object" && c in r));
  if (!present.length) {
    const first = rows[0] && typeof rows[0] === "object" ? rows[0] : {};
    present = Object.keys(first).filter((k) => first[k] === null || typeof first[k] !== "object").slice(0, 7);
  }
  if (!present.length) return JSON.stringify(rows, null, 2);
  const cells = rows.map((r) => present.map((c) => (r && typeof r === "object" ? cell(r[c]) : "")));
  const headers = present.map((c) => c.replace(/_/g, " ").toUpperCase());
  const widths = headers.map((h, i) => Math.min(Math.max(h.length, ...cells.map((row) => row[i].length)), 60));
  const budget = (process.stdout.columns || 120) - 2 * (widths.length - 1);
  while (widths.reduce((a, b) => a + b, 0) > budget && Math.max(...widths) > 10) widths[widths.indexOf(Math.max(...widths))]--;
  const line = (row) => row.map((c, i) => truncate(c, widths[i]).padEnd(widths[i])).join("  ").trimEnd();
  return [line(headers), ...cells.map(line)].join("\n");
}

function renderObject(data) {
  const width = Math.max(0, ...Object.keys(data).map((k) => k.length));
  return Object.entries(data)
    .filter(([, v]) => !(v === null || v === undefined || (Array.isArray(v) && !v.length) || (typeof v === "object" && !Array.isArray(v) && !Object.keys(v).length)))
    .map(([k, v]) => `${k.padEnd(width)}  ${truncate(cell(v), 100)}`)
    .join("\n");
}

function rowsAt(data, path) {
  if (path === "") return Array.isArray(data) ? data : null;
  if (Array.isArray(data)) return data;
  return data && typeof data === "object" && Array.isArray(data[path]) ? data[path] : null;
}

function emit(ctx, cmd, data) {
  if (data === null || data === undefined) {
    if (ctx.tty && !ctx.json) out("Done.");
    return;
  }
  const table = cmd.table;
  if (ctx.json || !ctx.tty || !table) return printJSON(data);
  if (table.kind === "object" && data && typeof data === "object" && !Array.isArray(data)) return out(renderObject(data));
  const rows = rowsAt(data, table.rows ?? "");
  if (!rows) return printJSON(data);
  const summary = table.summary && data && typeof data === "object" ? data[table.summary] : null;
  if (summary && typeof summary === "object") out(renderObject(summary) + "\n");
  out(renderTable(rows, table.columns));
}

// --- handlers --------------------------------------------------------------------

async function runSpecCommand(ctx, cmd, args, options) {
  const { method, path, query, body } = buildRequest(cmd, args, options);
  await confirm(ctx, cmd, args);
  const auth = cmd.auth !== false;
  if (cmd.output === "raw") {
    const content = await ctx.request(method, path, { query, body, auth, raw: true });
    if (options.out) {
      writeFileSync(options.out, content);
      err(`Wrote ${content.length} bytes to ${options.out}`);
    } else process.stdout.write(content);
    return 0;
  }
  emit(ctx, cmd, await ctx.request(method, path, { query, body, auth }));
  return 0;
}

const HANDLERS = {
  async login(ctx, cmd, args, options) {
    let key;
    if (options["with-token"]) key = readStdin().split(/\r?\n/)[0].trim();
    else if (ctx.flagApiKey) key = ctx.flagApiKey.trim();
    else {
      if (!process.stdin.isTTY) throw new CLIError("No terminal to prompt on; pipe the key in with 'trendsagi login --with-token'.", EXIT_USAGE);
      err(`Create an API key at ${SPEC.api_keys_url}`);
      key = (await ask("Paste your TrendsAGI API key: ", { hidden: true })).trim();
    }
    if (!key) throw new CLIError("No API key given.", EXIT_USAGE);
    if (!API_KEY_PREFIXES.some((prefix) => key.startsWith(prefix))) {
      throw new CLIError("That is not a TrendsAGI API key; keys start with ltc_live_.", EXIT_USAGE);
    }
    const profile = await ctx.request("GET", "/api/user/profile", { apiKey: key });
    const config = { ...ctx.config, api_key: key };
    if (ctx.baseURL !== DEFAULT_BASE_URL) config.base_url = ctx.baseURL;
    const path = writeConfig(config);
    err(`Logged in as ${profile?.email || "your account"}. Key saved to ${path}`);
    if (process.env.TRENDSAGI_API_KEY && process.env.TRENDSAGI_API_KEY !== key) {
      err("Note: TRENDSAGI_API_KEY is set and takes precedence over the saved key.");
    }
    return 0;
  },

  async logout(ctx) {
    const config = { ...ctx.config };
    if (!config.api_key) {
      err("Not logged in.");
      return 0;
    }
    delete config.api_key;
    const path = writeConfig(config);
    err(`Removed the saved key from ${path}. To revoke the key itself, delete it at ${SPEC.api_keys_url}`);
    return 0;
  },

  async whoami(ctx) {
    const profile = await ctx.request("GET", "/api/user/profile");
    const subscription = profile.subscription && typeof profile.subscription === "object" ? profile.subscription : {};
    const plan = [subscription.plan_name, subscription.name, subscription.plan].find((v) => typeof v === "string") || profile.stream_type;
    const info = {
      email: profile.email,
      name: profile.display_name,
      plan,
      organization: profile.organization && typeof profile.organization === "object" ? profile.organization.name : null,
      key_source: ctx.keySource,
      api: ctx.baseURL,
    };
    try {
      const usage = await ctx.request("GET", "/api/user/api-usage");
      if (usage?.summary) {
        info.requests_today = usage.summary.requests_today;
        info.daily_limit = usage.summary.plan_daily_limit;
      }
    } catch (error) {
      if (!(error instanceof APIError)) throw error;
    }
    if (ctx.json || !ctx.tty) printJSON(info);
    else out(renderObject(info));
    return 0;
  },

  async insights_generate(ctx, cmd, args, options) {
    const { method, path, body } = buildRequest(cmd, args, options);
    const queued = await ctx.request(method, path, { body });
    if (!options.wait) {
      emit(ctx, cmd, queued);
      return 0;
    }
    const taskId = queued?.task_id;
    let status = String(queued?.status || "").toUpperCase();
    const timeout = options.timeout ?? 180;
    const deadline = Date.now() + timeout * 1000;
    while (taskId && !TASK_DONE.has(status) && !TASK_FAILED.has(status)) {
      if (Date.now() > deadline) throw new CLIError(`Still running after ${timeout}s; check with 'trendsagi insights status ${taskId}'.`);
      await new Promise((resolve) => setTimeout(resolve, Number(process.env.TRENDSAGI_POLL_MS ?? 2000)));
      const result = await ctx.request("GET", `/api/trends/ai-insights/status/${encodeURIComponent(taskId)}`);
      status = String(result?.status || "").toUpperCase();
      if (TASK_FAILED.has(status)) throw new CLIError(`Insight generation failed: ${result?.error || status}`);
    }
    printJSON(await ctx.request("GET", `/api/trends/${args.trend_id}/ai-insights`));
    return 0;
  },

  async sql(ctx, cmd, args, options) {
    const { method, path, body } = buildRequest(cmd, args, options);
    if (!body?.query) throw new CLIError("Give a SELECT to run.", EXIT_USAGE);
    let result;
    try {
      result = await ctx.request(method, path, { body });
    } catch (error) {
      if (error instanceof APIError && error.body?.error) {
        const lines = [`Query refused (${error.body.error}): ${error.body.detail || error.detail}`];
        if (error.body.hint) lines.push(`Hint: ${error.body.hint}`);
        if (error.body.position) lines.push(`At character ${error.body.position}.`);
        throw new CLIError(lines.join("\n"));
      }
      throw error;
    }
    if (ctx.json || !ctx.tty) {
      printJSON(result);
      return 0;
    }
    const names = (result.columns || []).map((c) => c.name);
    const rows = (result.rows || []).map((row) => Object.fromEntries(names.map((n, i) => [n, row[i]])));
    out(renderTable(rows, names));
    let footer = `${result.row_count ?? rows.length} rows in ${result.elapsed_ms ?? "?"} ms`;
    if (result.truncated) footer += ` (truncated: ${result.truncated_reason || "limit reached"})`;
    err(footer);
    return 0;
  },

  async tools_call(ctx, cmd, args, options) {
    const toolArgs = options.args ?? {};
    if (!toolArgs || typeof toolArgs !== "object" || Array.isArray(toolArgs)) throw new CLIError("--args must be a JSON object.", EXIT_USAGE);
    for (const [key, raw] of options.arg || []) toolArgs[key] = jsonValue(raw);
    const result = (await ctx.request("POST", `/api/agent/tools/${encodeURIComponent(args.name)}`, { body: toolArgs })) || {};
    let output = (result.content || []).filter((c) => c && typeof c === "object").map((c) => c.text || "").join("\n");
    output = jsonValue(output);
    const text = typeof output === "string" ? output : JSON.stringify(output, null, 2);
    if (result.isError) {
      err(text);
      return EXIT_ERROR;
    }
    out(text);
    return 0;
  },

  async api(ctx, cmd, args, options) {
    const path = args.path.startsWith("/") ? args.path : `/${args.path}`;
    const query = Object.fromEntries(options.query || []);
    let body = options.data;
    if (options.field) {
      if (body === undefined) body = {};
      if (!body || typeof body !== "object" || Array.isArray(body)) throw new CLIError("--field needs --data to be a JSON object.", EXIT_USAGE);
      for (const [key, raw] of options.field) put(body, key, jsonValue(raw));
    }
    const method = (options.method || (body !== undefined ? "POST" : "GET")).toUpperCase();
    const content = await ctx.request(method, path, { query, body, auth: !options["no-auth"], raw: true });
    if (!content.length) return 0;
    try {
      printJSON(JSON.parse(content.toString("utf8")));
    } catch {
      process.stdout.write(content);
    }
    return 0;
  },

  async stream(ctx, cmd, args, options) {
    const apiKey = ctx.requireKey();
    if (typeof WebSocket !== "function") {
      throw new CLIError("'trendsagi stream' needs Node.js 22 or later (or the Python CLI: pip install trendsagi).");
    }
    const wsBase = ctx.baseURL.replace(/^http/, "ws");
    let url = `${wsBase}/ws/trends`;
    if (options.category) url = `${wsBase}/ws/category/${encodeURIComponent(options.category)}`;
    else if (options.follow?.length) url += `?follow=${options.follow.map(encodeURIComponent).join(",")}`;
    // Node's WebSocket (undici) accepts headers, which keeps the key out of the URL.
    const socket = new WebSocket(url, { headers: { "X-API-Key": apiKey, "User-Agent": USER_AGENT } });
    return new Promise((resolve, reject) => {
      socket.addEventListener("open", () => err(`Connected to ${url}; press Ctrl-C to stop.`));
      socket.addEventListener("message", async (event) => {
        let text = typeof event.data === "string" ? event.data : Buffer.from(await event.data.arrayBuffer?.() ?? event.data).toString("utf8");
        try {
          text = JSON.stringify(JSON.parse(text));
        } catch {}
        out(text);
      });
      socket.addEventListener("error", (event) => reject(new CLIError(`Stream ended: ${event.message || "connection failed"}`)));
      socket.addEventListener("close", () => resolve(0));
      process.once("SIGINT", () => {
        socket.close();
        resolve(0);
      });
    });
  },
};

// --- entry point -----------------------------------------------------------------

function describeError(error) {
  if (error instanceof CLIError) return [error.message, error.code];
  if (error instanceof APIError) {
    if (error.status === 401) return [`Authentication failed: ${error.detail}. Run 'trendsagi login' with a valid key.`, EXIT_AUTH];
    let message = `Error ${error.status}: ${error.detail}`;
    for (const key of ["hint", "upgrade_url", "message"]) {
      const extra = error.body?.[key];
      if (typeof extra === "string" && !message.includes(extra)) message += `\n${extra}`;
    }
    return [message, EXIT_ERROR];
  }
  return [error?.stack || String(error), EXIT_ERROR];
}

export async function main(argv = process.argv.slice(2)) {
  try {
    if (argv.length === 1 && ["--version", "-V"].includes(argv[0])) {
      out(`trendsagi ${VERSION}`);
      return 0;
    }
    if (argv[0] === "mcp" || argv[0] === "scaffold") {
      throw new CLIError(
        argv[0] === "mcp"
          ? "The local MCP server ships with the Python package (pip install \"trendsagi[mcp]\"). Or connect your AI client to the hosted server: https://api.trendsagi.com/mcp"
          : "'scaffold' ships with the Python package: pip install trendsagi",
        EXIT_USAGE,
      );
    }
    const parsed = parse(argv);
    if (parsed.version) {
      out(`trendsagi ${VERSION}`);
      return 0;
    }
    if (parsed.help) {
      out(helpText(parsed));
      return parsed.bare ? EXIT_USAGE : 0;
    }
    const ctx = new Context(parsed.globals);
    const handler = HANDLERS[parsed.cmd.handler] || runSpecCommand;
    return await handler(ctx, parsed.cmd, parsed.args, parsed.options);
  } catch (error) {
    const [message, code] = describeError(error);
    err(message);
    return code;
  }
}
