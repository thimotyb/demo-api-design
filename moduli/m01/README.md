# M01 — API styles side by side: REST, GraphQL and gRPC

Runnable examples for module M01 (API Design Fundamentals). The same checkout domain (orders, shipments, payments) is exposed three ways, so the styles can be compared on the same operations. All data is synthetic and held in memory; the payment gateway is simulated (the payment token selects the outcome).

Python 3.10+ is required. Everything runs offline after `pip install`.

```bash
./run_all.sh          # venv + dependencies + gRPC code generation + all tests + the measurement table
```

## Layout

| Folder | Style | What it shows |
| --- | --- | --- |
| [`shared/`](shared/domain.py) | — | Domain, simulated gateway, stable error codes, idempotent payment authorization |
| [`rest_api/`](rest_api/app.py) | REST, FastAPI | Resources and methods, status codes, `Idempotency-Key` header, `/v1` vs `/v2` |
| [`graphql_api/`](graphql_api/app.py) | GraphQL, Strawberry on FastAPI | Client-chosen fields, one endpoint, errors in the body, `@deprecated`; [field-level cache and cost-based rate limiting](graphql_api/policies.py) |
| [`grpc_api/`](grpc_api/proto/checkout/v1/checkout.proto) | gRPC, grpc.aio | Typed contract, status codes, metadata, deadlines, server streaming |
| [`compare/`](compare/measure.py) | REST vs GraphQL | Requests and bytes for the same screens |

gRPC is used where it fits: a call between internal services (order service → shipment service). The public API for a web client stays REST or GraphQL, because browsers cannot call gRPC without a proxy such as gRPC-Web.

## Examples and how to run them

| # | Example | Run |
| --- | --- | --- |
| 1 | Read an order with its shipment: REST needs two requests, GraphQL one query | `python -m compare.measure` |
| 2 | Authorize a payment idempotently: same key twice gives one payment | `pytest rest_api graphql_api -k "key or replay or retry"` |
| 3 | Errors: how each style reports the same failure | `pytest -k "not_found or conflict or transient or declined or invalid"` |
| 4 | Evolving a contract: `/v2`, deprecated GraphQL fields, protobuf field numbers | `pytest -k "v2 or evolution or old_message"` |
| 5 | gRPC: unary call, deadline, metadata, server streaming | `python -m grpc_api.server`, then `python -m grpc_api.client` |
| 6 | GraphQL field-level policies: per-field cache and query-cost rate limit | `pytest graphql_api/test_graphql_policies.py -v` |

Start each API by hand:

```bash
. .venv/bin/activate
uvicorn rest_api.app:app --port 8000        # http://127.0.0.1:8000/docs
uvicorn graphql_api.app:app --port 8001     # http://127.0.0.1:8001/graphql (GraphiQL)
python -m grpc_api.server                   # 127.0.0.1:50051; TrackShipment sends one live update per second
```

`SHIPMENT_STREAM_INTERVAL=0.2 python -m grpc_api.server` changes the pause between live updates (seconds).

The gRPC server has reflection enabled, so a generic client can explore it without the `.proto` file. With [grpcurl](https://github.com/fullstorydev/grpcurl), installed by [`grpc_api/install_grpcurl.sh`](grpc_api/install_grpcurl.sh) (Linux and macOS, no sudo; into `~/.local/bin` or the directory you pass; the download is checked against a pinned SHA-256):

```bash
grpc_api/install_grpcurl.sh
grpcurl -plaintext 127.0.0.1:50051 list
grpcurl -plaintext 127.0.0.1:50051 describe checkout.v1.ShipmentService
grpcurl -plaintext -d '{"tracking_code": "TRK-1001"}' 127.0.0.1:50051 checkout.v1.ShipmentService/GetShipment
grpcurl -plaintext -d '{"tracking_code": "TRK-1001"}' 127.0.0.1:50051 checkout.v1.ShipmentService/TrackShipment
```

## Measured difference (REST vs GraphQL)

From `python -m compare.measure`, in-process, synthetic data:

| Screen | Style | Requests | Bytes sent | Bytes received | Total |
| --- | --- | --- | --- | --- | --- |
| A. status line (2 fields) | REST | 2 | 0 | 789 | 789 |
| A. status line (2 fields) | GraphQL | 1 | 84 | 91 | 175 |
| B. detail screen (all fields) | REST | 2 | 0 | 789 | 789 |
| B. detail screen (all fields) | GraphQL | 1 | 246 | 777 | 1023 |

GraphQL removes the extra round trip in both screens and saves most bytes when the client needs few fields. When the client needs everything, the query text makes the total larger than REST's. The first rows are not a general result: they depend on this payload.

## How each style reports the same failure

| Situation | REST | GraphQL | gRPC |
| --- | --- | --- | --- |
| Unknown resource | `404`, body `{"code": "ORDER_NOT_FOUND", ...}` | HTTP `200`, `errors[0].extensions.code = ORDER_NOT_FOUND`, `data: null` | `NOT_FOUND`, trailing metadata `x-error-code` |
| Invalid input | `400` `INVALID_REQUEST` | `errors` entry (schema errors are rejected before execution) | `INVALID_ARGUMENT` |
| Payment declined or gateway failure | `402` with `PAYMENT_DECLINED` / `TRANSIENT_GATEWAY_FAILURE` | `errors` entry with the same codes | — (not part of the internal contract) |
| Idempotency key reused with another request | `409` `IDEMPOTENCY_CONFLICT` | `errors` entry with the same code | — |
| Slow dependency | client timeout | client timeout | `DEADLINE_EXCEEDED` from the call deadline |

Because GraphQL answers `200` even on failure, monitoring and retries must look at the `errors` array, not only the HTTP status.

## Caching and rate limiting when there is one endpoint

A GraphQL server receives every operation on one URL with one method, so the usual infrastructure policies cannot tell operations apart. The server is also an aggregation layer: its resolvers call the backing services, much like a gateway or backend-for-frontend. Policies therefore move inside the GraphQL layer ([`graphql_api/policies.py`](graphql_api/policies.py)).

| Concern | REST | GraphQL (this example) |
| --- | --- | --- |
| Caching | `Cache-Control` on `GET /v1/orders/{id}/shipment`; browser, proxy or CDN cache it with no application code | `POST` is not cacheable by URL. The `Order.shipment` field is cached in its resolver (`CachedField`, 30 s TTL, keyed by tracking code), so queries with different selections share one carrier call |
| Rate limiting | Count requests per route and client | A request count cannot see cost. Each query is priced from its fields before execution (`COSTS`: `shipment` 5, `lines` 2, `events` 3, ...) and spent from a per-client token bucket (20 points, 10 per second) |
| Refusal | `429` and `Retry-After` | `429` and `Retry-After` at the transport, plus a coded error `RATE_LIMITED` with `cost`, `remaining` and `retryAfterSeconds` in the body |

What the tests show (`graphql_api/test_graphql_policies.py`):

- Repeated or differently shaped queries for the same shipment make one carrier lookup; the entry expires after its TTL.
- A field without the policy (`customer`) is resolved every time.
- Twenty cheap requests pass for one client, while the third `status line` query (7 points each) is refused: counting HTTP requests would treat both groups alike.
- A refused query is not executed, the budget refills over time, and clients have separate budgets.

Limits of the example: costs are fixed per field with no multiplier for list sizes or pagination arguments; the cache and the buckets are in memory and per process; cached data must not depend on the caller (a cache key without the user must never hold personal data); there is no query depth limit, which a production endpoint also needs.

## Idempotency rules implemented

- Same key and same request: the stored payment is returned (REST `200` with `Idempotent-Replayed: true`; GraphQL `replayed: true`); the gateway is not called again.
- Same key and a different request: conflict.
- Transient gateway failure: not stored, so a retry with the same key reaches the gateway again.
- Definitive refusal: stored, and replayed as the same refusal.
- No key: every request creates a payment.

The store is in memory and single-process. A real service needs a shared store (database or Redis) with an expiry policy, and must handle two concurrent requests that carry the same key.

## Limits

- No authentication (see module M03), no persistence, one process. The cache and rate-limit state are also per process.
- Byte counts are body sizes only; HTTP headers, compression, protobuf and HTTP/2 framing are not measured.
- gRPC bidirectional streaming is not covered.
