# OpenAPI client example for M3

This folder is a ready-to-use example for `openapi-python-client` based on the M3 FastAPI Orders API.

## What is inside

- `openapi.json`: OpenAPI snapshot for the M3 Orders API, with the `OAuth2ClientCredentials` security scheme and the `401` and `403` responses (the live server publishes the same scheme at `/openapi.json`)
- `generate_client.py`: helper that regenerates a client package if `openapi-python-client` is installed
- `m3_orders_api_demo_client/`: lightweight client package that matches the M3 API shape
- `demo.py`: end-to-end example that fetches a Keycloak token and calls the protected endpoints

## Quick start

1. Start the M3 stack from the example root:

```bash
cd moduli/m03
python scripts/start-keycloak-local.py
```

2. In another shell, start the API server:

```bash
cd moduli/m03/server
uvicorn app.main:app --host 127.0.0.1 --port 8001
```

3. Run the demo client:

```bash
cd moduli/m03/openapi-python-client
python demo.py
```

## Regenerate a client from the OpenAPI snapshot

If you want to rebuild a generated client package from the snapshot, install the generator and run the helper:

```bash
cd moduli/m03/openapi-python-client
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
python generate_client.py
```

The generator command writes the client package according to the OpenAPI contract exposed by the M3 server.

