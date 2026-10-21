# M03 — OAuth2 password flow without an external identity provider

The base authentication tutorial of FastAPI, in four runnable steps. The API issues and checks its own tokens, so no Keycloak is needed. For an external identity provider see the [Keycloak example](../README.md) in the parent folder.

```bash
./run_all.sh          # virtual environment + dependencies + tests of the four steps
```

Python 3.10 or later is required. To try a step by hand:

```bash
. .venv/bin/activate
uvicorn oauth2_jwt:app --reload     # or simple_oauth2:app; then open http://127.0.0.1:8000/docs and press Authorize
```

| Step | File | FastAPI tutorial page | What it adds |
| --- | --- | --- | --- |
| 1 | [`first_steps.py`](first_steps.py) | [First Steps](https://fastapi.tiangolo.com/tutorial/security/first-steps/) | `OAuth2PasswordBearer(tokenUrl="token")`: the scheme, the Authorize button, `401` without a bearer token. The token is not checked |
| 2 | [`get_current_user.py`](get_current_user.py) | [Get Current User](https://fastapi.tiangolo.com/tutorial/security/get-current-user/) | A `User` model and a `get_current_user` dependency on top of the scheme |
| 3 | [`simple_oauth2.py`](simple_oauth2.py) | [Simple OAuth2 with Password and Bearer](https://fastapi.tiangolo.com/tutorial/security/simple-oauth2/) | `POST /token` with `OAuth2PasswordRequestForm`, user lookup, `get_current_active_user`, `400` and `401` answers. The token is the username |
| 4 | [`oauth2_jwt.py`](oauth2_jwt.py) | [OAuth2 with Password (and hashing), Bearer with JWT tokens](https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/) | Argon2 password hashes (`pwdlib`), a signed JWT with `sub` and `exp` (`PyJWT`, HS256), `401` for any invalid token, the `Token` response model |

Users of steps 3 and 4: `johndoe` / `secret` (active) and `alice` / `secret2` (disabled).

Try the flow with `curl`:

```bash
curl -s -X POST http://127.0.0.1:8000/token -d "username=johndoe&password=secret"
curl -s http://127.0.0.1:8000/users/me -H "Authorization: Bearer johndoe"
```

With step 4 the token is a JWT and the route has a trailing slash:

```bash
TOKEN=$(curl -s -X POST http://127.0.0.1:8000/token -d "username=johndoe&password=secret" | python3 -c "import sys, json; print(json.load(sys.stdin)['access_token'])")
curl -s http://127.0.0.1:8000/users/me/ -H "Authorization: Bearer $TOKEN"
```

Paste the token into [jwt.io](https://jwt.io) or decode its middle part with base64 to see `sub` and `exp`: the payload is signed, not encrypted.

## Differences from the tutorial

- `GET /users/me` in step 3 declares `response_model=User`. Without it the route returns the `UserInDB` object and the response contains `hashed_password`; a test covers this.
- Step 4 reads `SECRET_KEY` from the environment (the tutorial hard-codes it) and keeps the tutorial's `401` on a failed login, where step 3 answers `400`.
- Type hints on `fake_hash_password`, `get_user` and `fake_decode_token`, comments, and tests (`test_password_flow.py`).

## What this does not prove

- In steps 1 to 3 the "hash" is a prefix and the access token is the username, so anybody who knows a username can forge a token (a test documents it). Step 4 removes both.
- Step 4 signs with a symmetric key (HS256) whose default value is public in this repository: set `SECRET_KEY` (`openssl rand -hex 32`) for anything beyond the demo. Asymmetric signing (RS256) and key rotation are not covered.
- No refresh token, revocation (a stolen token is valid until `exp`) or rate limiting. Users are in a dictionary in memory, and there is no HTTPS.
