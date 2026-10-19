# Developer portal with Zudoku (M06)

A small [Zudoku](https://zudoku.dev) site that publishes the checkout contract as an API reference next to hand-written guides.

- `zudoku.config.ts` — site title, navigation and the OpenAPI source. The source is the contract of [`../../m05/step-01-contratto/openapi/checkout-api.yaml`](../../m05/step-01-contratto/openapi/checkout-api.yaml), so the reference cannot drift from the contract used by the mock.
- `pages/*.mdx` — the guides (introduction, errors and retries).

## Run

Node.js 22.22 or later is required.

```bash
npm install
npm run dev      # http://localhost:3000 with hot reload
npm run build    # static site in dist/
npm run preview  # serve the production build
```

## What it does not show

- The page content and the examples are fixtures from the mock profile. The portal renders the contract; it does not verify retry, persistence or server-side idempotency.
- The playground sends requests to the server URL in the contract (the Prism mock on `127.0.0.1:4010`). Start the mock from `../../m05/step-01-contratto/` first.
- API keys, subscriptions and per-user access need a gateway or an API management product; this site is static documentation.
