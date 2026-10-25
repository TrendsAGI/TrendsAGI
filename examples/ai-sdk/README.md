# Vercel AI SDK + `@trendsagi/ai` example

```bash
# from the repository root
npm install
npm run build

cd examples/ai-sdk
cp .env.example .env
# edit .env
npm start
```

Requires `OPENAI_API_KEY` and `TRENDSAGI_API_KEY` for a real `generateText`
call. Without `OPENAI_API_KEY` the example prints the tool list and executes
`list_trends` against a mock TrendsAGI response.

```bash
set -a && . ./.env && set +a && npm start
```
