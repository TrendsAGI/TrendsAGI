# OpenAI + `@trendsagi/openai` example

```bash
# from the repository root
npm install
npm run build

cd examples/openai
cp .env.example .env
# edit .env
npm start
```

Requires `OPENAI_API_KEY` and `TRENDSAGI_API_KEY` for a real model turn.
Without `OPENAI_API_KEY` the example prints the tool definitions and runs
`runTrendsAGITool` against a mock TrendsAGI response, so no credentials are
needed to inspect the integration.

Run it with the env file loaded:

```bash
set -a && . ./.env && set +a && npm start
```
