# M3 - Keycloak JWT protected API

This example shows a complete OAuth2 `client_credentials` flow with:

- Keycloak running locally from the official distribution
- a small FastAPI Orders API protected by Bearer JWT
- a Python client that fetches a token, reads orders, and creates a new one
- a Postman collection that walks through the same steps

## What this example demonstrates

1. Keycloak issues an access token using the OAuth2 `client_credentials` grant.
2. The FastAPI server validates the JWT signature and issuer.
3. The server only accepts requests with a valid `Authorization: Bearer <token>` header.
4. The client authenticates against Keycloak and then calls the protected endpoint.
5. Postman can reproduce the same flow step by step.

## Related example

- [`fastapi-password-flow/`](fastapi-password-flow/README.md): the FastAPI OAuth2 password-flow tutorial in four steps (the last with password hashing and JWT), without an external identity provider.

## Folder layout

- `scripts/start-keycloak-local.py`: launcher for a local Keycloak distribution
- `docker-compose.yml`: optional Docker-based alternative
- `keycloak/realm/m3-jwt-realm.json`: imported realm with two confidential clients, the realm roles `orders:read` and `orders:write` and the service accounts that hold them
- `server/`: FastAPI resource server
- `client/`: script that authenticates and calls the API
- `postman/`: collection and playbook
- `openapi-python-client/`: ready-to-run client example and OpenAPI snapshot

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

## Roles

| Client | Secret | Realm roles of its service account | Can do |
| --- | --- | --- | --- |
| `m3-fastapi-client` | `m3-fastapi-secret` | `orders:read`, `orders:write` | read and create orders |
| `m3-readonly-client` | `m3-readonly-secret` | `orders:read` | read orders; `POST /orders` returns `403` |

In the Keycloak console, switch to the realm `M3 JWT demo`. The roles are under **Realm roles**. The roles of a client are under **Clients → the client → Service account roles**. The roles appear in the access token in the claim `realm_access.roles`.

The realm is imported only when it does not exist yet. A realm imported from an older version of the realm file has no web origins on its clients, and then Authorize in `/docs` fails with `Failed to fetch` and a CORS error in the browser console (`No 'Access-Control-Allow-Origin' header`): add `http://localhost:8001` and `http://127.0.0.1:8001` to **Web origins** in the settings of each client, or reset the realm as described here. If you started Keycloak before this change, delete the realm `m3-jwt` in the console, or delete `.keycloak/keycloak-<version>/data/h2`, and start Keycloak again.

The role tests do not need Keycloak:

```bash
. .venv/bin/activate
pip install pytest httpx
cd server && python -m pytest
```

## Notes

- The realm is imported automatically at Keycloak startup.
- The API verifies the JWT using the realm public keys exposed by Keycloak.
- The protected endpoint checks the `azp` claim and accepts only tokens minted for the configured clients (`KEYCLOAK_EXPECTED_AZP`, a comma-separated list).
- The API declares the OAuth2 client credentials flow as a security scheme (`OAuth2ClientCredentials`, token URL `KEYCLOAK_TOKEN_URL`), so `http://127.0.0.1:8001/docs` shows the **Authorize** button and a lock on each protected operation. In the dialog enter a client id and secret (for example `m3-readonly-client` / `m3-readonly-secret`): Swagger UI gets the token from Keycloak, which accepts the request because the clients list `http://localhost:8001` and `http://127.0.0.1:8001` as web origins (CORS).
- Authorization uses realm roles: the `GET` endpoints require `orders:read` and `POST /orders` requires `orders:write` (the `require_role` dependency in `server/app/main.py`). A valid token without the role gets `403`.
- If you prefer Docker, `docker-compose.yml` remains available as an alternative launch path.
