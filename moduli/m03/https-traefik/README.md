# M03 — The Orders API over HTTPS with Traefik

The M3 laboratory of the parent folder runs over plain HTTP. This folder is an **autonomous, additional** example: the same Keycloak realm and the same Orders API, behind a reverse proxy ([Traefik](https://doc.traefik.io/traefik/)) that ends TLS. The HTTP laboratory is not modified, and it only shares the API source: the image is built from `../server`.

```
browser / curl ──HTTPS──▶ Traefik ──HTTP, private network──▶ Keycloak   https://auth.m3.localhost
                          :80 → redirect to HTTPS         └─▶ Orders API https://api.m3.localhost
```

Requirements: Docker with Compose, `openssl`, `curl`, `python3`. Ports 80 and 443 must be free.

## Run it

```bash
./certs/make-certs.sh          # a local CA and a server certificate (certs/*.pem, certs/*.key)
docker compose up -d --build
./check.sh                     # smoke test of the whole flow over HTTPS
docker compose down            # stop it
```

Wait about 30 seconds after `up` for Keycloak to import the realm. Then open:

- `https://api.m3.localhost/docs`: the interactive documentation. **Authorize** asks the token to `https://auth.m3.localhost`, with `m3-fastapi-client` / `m3-fastapi-secret` or `m3-readonly-client` / `m3-readonly-secret`.
- `https://auth.m3.localhost`: the Keycloak console (`admin` / `admin`).

The names `*.localhost` resolve to the local machine in browsers and in `curl`, so no `hosts` file entry is needed.

## Trusting the certificate

The certificate is signed by a CA created on your machine, so nothing trusts it yet:

- `curl --cacert certs/ca.pem https://api.m3.localhost/` trusts it for one command. Without `--cacert`, `curl` refuses the connection (exit code 60): this is what protects a client from a fake server.
- A browser shows a warning until you import `certs/ca.pem` as a trusted authority (Windows: *Manage computer certificates* → *Trusted Root Certification Authorities*; Chrome and Edge use it). Remove it when you no longer need the example.

Never import or share `certs/ca.key`: whoever holds it can issue certificates that your browser trusts. The `certs/` folder is git-ignored for this reason.

## What changes compared with the HTTP laboratory

| Setting | HTTP laboratory | This example |
| --- | --- | --- |
| Keycloak address and token `iss` | `http://localhost:8080/realms/m3-jwt` | `https://auth.m3.localhost/realms/m3-jwt` (`KC_HOSTNAME`) |
| `KEYCLOAK_ISSUER` of the API | the same HTTP address | the HTTPS address: it must match the `iss` claim |
| `KEYCLOAK_TOKEN_URL` (Authorize in `/docs`) | HTTP | HTTPS |
| JWKS (`KEYCLOAK_JWKS_URL`) | `http://localhost:8080/...` | `http://keycloak:8080/...` on the private Docker network, never through the Internet |
| Web origins of the clients (CORS) | `http://localhost:8001`, `http://127.0.0.1:8001` | `https://api.m3.localhost` (`realm/m3-jwt-realm.json`) |
| Keycloak and uvicorn flags | none | `KC_PROXY_HEADERS=xforwarded`, `--proxy-headers`: trust `X-Forwarded-Proto` from the proxy |

`check.sh` verifies: the certificate chain and TLS version; that a client without the CA refuses the connection; the redirect from HTTP to HTTPS; the `401`, `403` and `200` or `201` answers of the roles; the HTTPS issuer inside the token; the HTTPS token URL in the OpenAPI document.

## Let's Encrypt on a real server

`docker-compose.letsencrypt.yml` replaces the local certificate with certificates that Let's Encrypt issues and renews on its own. The [FastAPI documentation](https://fastapi.tiangolo.com/deployment/https/) describes the same idea: a TLS termination proxy such as Traefik, with Let's Encrypt as certificate authority.

```bash
cp .env.example .env     # set API_HOST, AUTH_HOST and ACME_EMAIL
docker compose -f docker-compose.yml -f docker-compose.letsencrypt.yml up -d
```

In `realm/m3-jwt-realm.json` also replace the web origin `https://api.m3.localhost` with `https://<your API_HOST>`.

**This variant is not tested end to end here.** Let's Encrypt has to reach your server: you need a public domain with DNS records for the two hostnames pointing to the machine, and ports 80 and 443 open from the Internet. What was checked: the merged Compose file is valid, and Traefik expands the hostnames in `traefik/dynamic.letsencrypt.yml` and starts requesting certificates (which Let's Encrypt refuses for the placeholder `example.com`). Try it first with the staging server (the commented `caserver` line): it has no rate limits, and its certificates are not trusted by browsers.

## What this does not prove

- It is a teaching setup: Keycloak runs with `start-dev`, the admin password is `admin`, the client secrets are public in the repository and the data is in memory.
- Traffic between Traefik and the containers is plain HTTP on a private network. That is common, but if the network is not private (several hosts) the internal hops need TLS too.
- TLS protects the data in transit and checks the identity of the server. It does not authenticate the user: that is still the job of the token. Security headers such as HSTS, certificate pinning, mutual TLS and rate limits at the proxy are not configured.
- The Postman collection of the parent folder uses HTTP addresses and is not adapted.
