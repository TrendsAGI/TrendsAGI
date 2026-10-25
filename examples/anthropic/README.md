# Anthropic + `@trendsagi/anthropic` example

```bash
# from the repository root
npm install
npm run build

cd examples/anthropic
cp .env.example .env
# edit .env
npm start
```

Requires `ANTHROPIC_API_KEY` and `TRENDSAGI_API_KEY` for a real Claude turn.
Without `ANTHROPIC_API_KEY` the example prints the tool definitions and runs
`runAnthropicTool` against a mock TrendsAGI response.

```bash
set -a && . ./.env && set +a && npm start
```
