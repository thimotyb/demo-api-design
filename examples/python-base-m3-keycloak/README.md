# M3 - Keycloak JWT protected API

This example shows a complete OAuth2 `client_credentials` flow with:

- Keycloak running locally from the official distribution
- a small FastAPI Orders API protected by Bearer JWT
- a Python client that fetches a token, reads orders, and creates a new one
- a Postman collection that walks through the same steps

## Published copy

Some files from this example are also published under `site/examples/m3-keycloak-client-credentials/` so they can be reached when the static site is served locally from `site/`.
The source of truth for the example remains this folder under `examples/`.

## What this example demonstrates

1. Keycloak issues an access token using the OAuth2 `client_credentials` grant.
2. The FastAPI server validates the JWT signature and issuer.
3. The server only accepts requests with a valid `Authorization: Bearer <token>` header.
4. The client authenticates against Keycloak and then calls the protected endpoint.
5. Postman can reproduce the same flow step by step.

## Folder layout

- `scripts/start-keycloak-local.py`: launcher for a local Keycloak distribution
- `docker-compose.yml`: optional Docker-based alternative
- `keycloak/realm/m3-jwt-realm.json`: imported realm with a confidential client
- `server/`: FastAPI resource server
- `client/`: script that authenticates and calls the API
- `postman/`: collection and playbook
- `openapi-python-client/`: ready-to-run client example and OpenAPI snapshot

When browsing the course site locally, the published copies are available at:

- `site/examples/m3-keycloak-client-credentials/README.md`
- `site/examples/m3-keycloak-client-credentials/notebook/M3-Keycloak-JWT-Demo.ipynb`
- `site/examples/m3-keycloak-client-credentials/postman/README.md`
- `site/examples/m3-keycloak-client-credentials/openapi-python-client/README.md`

## Quick start

1. From the example root, create and activate the shared virtual environment:

```bash
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
```

2. Start Keycloak locally in a separate terminal:

```bash
python scripts/start-keycloak-local.py
```

3. In another terminal, start the API server:

```bash
. .venv/bin/activate
cd server
uvicorn app.main:app --host 127.0.0.1 --port 8001
```

4. Run the client:

```bash
. .venv/bin/activate
python client/client.py
```

5. Open the API docs:

- `http://127.0.0.1:8001/docs`

The API exposes:

- `GET /orders`: list order headers
- `GET /orders/{order_id}`: read one order with all rows
- `GET /orders/{order_id}/lines`: read only the order rows
- `POST /orders`: create a new order with header and rows

6. Open Keycloak:

- `http://localhost:8080`

Note for WSL users: in this setup `localhost` works from the Windows browser, while `127.0.0.1:8080` may refuse the connection.

## Default credentials

Keycloak admin:

- username: `admin`
- password: `admin`

OAuth2 client:

- client id: `m3-fastapi-client`
- client secret: `m3-fastapi-secret`

Realm:

- `m3-jwt`

## Notes

- The realm is imported automatically at Keycloak startup.
- The API verifies the JWT using the realm public keys exposed by Keycloak.
- The protected endpoint checks the `azp` claim and accepts only tokens minted for the configured client.
- If you prefer Docker, `docker-compose.yml` remains available as an alternative launch path.
