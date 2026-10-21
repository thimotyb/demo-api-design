# Security Audit — M3 Keycloak Client Credentials Demo

Data: 2026-05-18

## ALTA PRIORITÀ

### 1. Audience (`aud`) non verificata — `auth.py:41`

```python
options={"verify_aud": False},
```

La validazione del claim `aud` è disabilitata. Secondo RFC 7519, il server delle risorse deve verificare che il token sia stato emesso per sé stesso. Senza questa verifica, un token ottenuto per un'altra applicazione nello stesso realm potrebbe essere accettato. Il controllo su `azp` (riga 51) è una misura di attenuazione parziale ma non è un sostituto standard per `aud`.

**Fix:** aggiungere `"m3-fastapi-server"` come audience nel client Keycloak, poi rimuovere `verify_aud: False` e passare `audience="m3-fastapi-server"` a `jwt.decode`.

---

## MEDIA PRIORITÀ

### 2. Nessun RBAC applicato — `main.py` (tutti gli endpoint)

Il realm definisce il ruolo `api-access` ma il server non lo verifica mai. Qualsiasi service account del realm può chiamare tutti gli endpoint senza restrizioni di ruolo.

### 3. Order ID sequenziale prevedibile — `orders.py:46`

Gli ID partono da 1001 e si incrementano. Un client autenticato può enumerare tutti gli ordini di altri client (`/orders/1001`, `/orders/1002`, …). Non c'è isolamento per client.

### 4. Comunicazione HTTP in chiaro

Tutti i token viaggiano su HTTP. In un ambiente non localhost, un attaccante MITM può intercettare i Bearer token. Il JWKS viene anch'esso scaricato su HTTP (senza TLS pinning), aprendo la porta alla sostituzione delle chiavi pubbliche.

---

## BASSA PRIORITÀ / ACCETTABILE PER UN DEMO

| Problema | File | Note |
|---|---|---|
| Secret client hardcoded `m3-fastapi-secret` | `keycloak/realm/m3-jwt-realm.json`, `client/client.py:15` | Comune nei demo; in prod usare vault o secret manager |
| Credenziali Keycloak `admin/admin` | `docker-compose.yml:6-7`, `scripts/start-keycloak-local.py:73` | Solo dev mode, mai esporre in prod |
| Nessun checksum al download di Keycloak | `scripts/start-keycloak-local.py:17-19` | Il file viene scaricato da HTTPS ma senza verifica del digest |
| Nessun rate limiting | `server/app/main.py` | Nessun middleware di throttling sugli endpoint protetti |
| Nessun CORS configurato | `server/app/main.py` | FastAPI permette tutte le origin di default |
| `lru_cache` su settings | `server/app/auth.py:10,23` | Se le env var cambiano a runtime la cache non si aggiorna (non problema in container) |

---

## Riepilogo

Il problema strutturalmente più rilevante è la **disabilitazione della verifica `aud`**: non è una semplificazione da demo, è una prassi scorretta che potrebbe essere copiata in produzione. Tutti gli altri problemi sono tipici di un ambiente locale di sviluppo e sono accettabili nel contesto di un esempio didattico, a patto di documentarli chiaramente.
