# Developer portal with Zudoku (M06)

A small [Zudoku](https://zudoku.dev) site that publishes the checkout contract as an API reference next to hand-written guides.

- `zudoku.config.ts` — site title, navigation and the OpenAPI source. The source is the contract of [`../../m07/openapi/checkout-api.yaml`](../../m07/openapi/checkout-api.yaml), so the reference cannot drift from the contract used by the mock.
- `zudoku.build.ts` — a build-time processor that renders `../../../caso-guida/req-seq-payment-retry.puml` to SVG through the PlantUML server and appends it to the `POST /payments` description. The contract is not modified, and `public/diagrams/` is generated (not committed).
- `pages/*.mdx` — the guides (introduction, errors and retries).

## Run

Node.js 22.22 or later and Java are required. The diagram is rendered by a local PlantUML server, which [`../scripts/plantuml-server.sh`](../scripts/plantuml-server.sh) downloads once (version and SHA-256 pinned, cached in `../.cache/`) and runs on `127.0.0.1:18080`. `npm run dev` and `npm run build` start it first if it is not running; nothing is sent to an external renderer. Set `PLANTUML_SERVER` to use another server.

```bash
npm install
npm run dev      # http://localhost:3000; the SVG is rendered again when the .puml changes (reload the page)
npm run build    # static site in dist/
npm run preview  # serve the production build
npm run plantuml:stop   # stop the PlantUML server when you are done
```

## What it does not show

- The page content and the examples are fixtures from the mock profile. The portal renders the contract; it does not verify retry, persistence or server-side idempotency.
- The playground sends requests to the server URL in the contract (the Prism mock on `127.0.0.1:4010`). Start the mock from `../../m07/` first.
- API keys, subscriptions and per-user access need a gateway or an API management product; this site is static documentation.
