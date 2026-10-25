# LangChain + `@trendsagi/langchain` example

```bash
# from the repository root
npm install
npm run build

cd examples/langchain
cp .env.example .env
# edit .env
npm start
```

Requires `OPENAI_API_KEY` and `TRENDSAGI_API_KEY` for a real model turn.
Without `OPENAI_API_KEY` the example prints the tool list and invokes
`list_trends` against a mock TrendsAGI response.

```bash
set -a && . ./.env && set +a && npm start
```
