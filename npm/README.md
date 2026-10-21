# trendsagi

The TrendsAGI command line: what is trending on social platforms right now, with measured volume, velocity and growth, AI insights on why each topic is moving, evidence-backed recommendations, crisis events, your watchlist and read-only SQL, from a terminal or a shell script. No dependencies; Node.js 18 or later.

```bash
npx trendsagi login              # paste an API key from app.trendsagi.com > Profile > API Keys
npx trendsagi trends list --category Technology --sort velocity --limit 10
```

Or install it once:

```bash
npm install -g trendsagi
trendsagi --help
```

## Examples

```bash
trendsagi trends list --sort velocity --limit 10          # fastest-moving topics
trendsagi trends analytics 123 --period 7d                # one trend's readings over time
trendsagi insights get 123                                # audience, sentiment and marketing angles
trendsagi insights generate 123 --wait                    # build fresh insights, then print them
trendsagi recommendations list --priority high            # prioritised actions with their evidence
trendsagi crisis list --status active
trendsagi watchlist add "oat milk" --threshold 50000 --email
trendsagi schema                                          # tables the sql command can read
trendsagi sql "SELECT category, count(*) FROM trends GROUP BY 1 ORDER BY 2 DESC"
trendsagi webhooks create --url https://example.com/hooks/trends --trigger trend_velocity --threshold 50
trendsagi ads preview meta_ads --trend 123 --level ad_group
trendsagi stream --follow "AI,#SaaS"                      # live updates as JSON lines (Node.js 22+)
trendsagi api /api/integrations/delivery/health -q lookback_hours=24   # any endpoint
```

| Commands | What they do |
| --- | --- |
| `login`, `logout`, `whoami` | Save, forget and check the API key |
| `trends` | Trending topics: `list`, `get`, `analytics`, `categories`, `autocomplete` |
| `insights` | AI insights: `get`, `generate`, `status`, `search` |
| `recommendations` (`recs`) | `list`, `action`, `feedback` |
| `crisis` | `list`, `action` (acknowledge, archive, reopen) |
| `watchlist` | `list`, `add`, `remove` |
| `sql`, `schema` | One read-only PostgreSQL SELECT over your data, and the tables it can read |
| `tools`, `find` | The agent tools (`list`, `call`), and whether TrendsAGI can do a task |
| `webhooks`, `exports` | Create, change, test and run webhooks and data exports |
| `ads` | Connected ad platforms: `providers`, `resources`, `preview`, `apply`, `streams`, `report`, `report-export` |
| `integrations` | `availability`, `status`, `health`, `value` |
| `stream` | Live trend updates |
| `usage`, `status`, `api` | API usage, service status, and any endpoint without its own command |

## How it behaves

- **Key:** `--api-key`, then `TRENDSAGI_API_KEY`, then the key `trendsagi login` saved to `~/.config/trendsagi/config.json` (`%APPDATA%\trendsagi` on Windows). The Python CLI (`pip install trendsagi`) reads the same file.
- **Output:** lists print as tables in a terminal, and as JSON when piped or with `--json`: `trendsagi trends list | jq '.trends[].name'`.
- **Safety:** commands that delete something or change live ads ask first; pass `--yes` in scripts.
- **Exit codes:** 0 success, 1 API or request error, 2 invalid usage, 4 missing or rejected API key.
- **Usage:** each command is the API request it makes and counts against your plan's daily limit.

Run `trendsagi <command> --help` for every option. Guide: [trendsagi.com/api-docs/integrations/cli](https://trendsagi.com/api-docs/integrations/cli). API reference: [trendsagi.com/api-docs/reference](https://trendsagi.com/api-docs/reference).

## Also from TrendsAGI

- Python client, agent tools and a local MCP server: `pip install trendsagi`
- Hosted MCP server for Claude, ChatGPT, Grok and Cursor: `https://api.trendsagi.com/mcp` ([setup](https://trendsagi.com/mcp))

Source: [github.com/TrendsAGI/TrendsAGI](https://github.com/TrendsAGI/TrendsAGI/tree/main/npm). MIT licensed.
