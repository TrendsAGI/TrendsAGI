# `@trendsagi/core` example

```bash
# from the repository root
npm install
npm run build

cd examples/core
npm start
```

Without `TRENDSAGI_API_KEY` the example uses a mock `fetch` and needs no
network or credentials. With a key in `.env` (or the environment) it calls the
real API.

```bash
cp .env.example .env
# edit .env
set -a && . ./.env && set +a
npm start
```

Expected output with the mock:

```text
[ '#AIUpdate', 'skin barrier repair' ]
```
