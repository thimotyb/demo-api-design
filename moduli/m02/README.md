# M02 — FastAPI core concepts

Two small, heavily commented implementations of the Orders API described in module M02 of the course. The code is deliberately simple: no authentication, no error handling beyond a 404, no database. The data is a dict in memory, so it is lost when the server stops.

```bash
./run_all.sh          # virtual environment + dependencies + tests of both versions + timing demo
```

Python 3.10 or later is required.

| Folder | What it is |
| --- | --- |
| [`orders_api/`](orders_api/) | The Orders API with plain `def` operations |
| [`orders_api_async/`](orders_api_async/) | The same API with `async def` / `await`, plus endpoints that show what async changes |

## Run an API

```bash
. .venv/bin/activate                 # after ./run_all.sh has created it
cd orders_api                        # or orders_api_async
uvicorn app.main:app --reload        # http://127.0.0.1:8000/docs
```

## What each lesson topic maps to

| Topic in the module | Where to read it |
| --- | --- |
| First application, `GET /` | `app/main.py` (`root`) |
| Application lifecycle (lifespan) | `app/main.py` (`lifespan`) |
| GET, POST, PUT, PATCH, DELETE | `app/routers/orders.py` |
| Path, query and body parameters | `get_order` (path), `list_orders` (query), `create_order` (body) |
| Pydantic models: constraints, defaults, aliases | `app/models.py` (`Field`, `default_factory`, `alias="orderDate"`) |
| Separate input and output models, `response_model` | `OrderCreate` in, `OrderSummary` / `OrderDetail` out |
| `HTTPException` for a missing resource | `get_order_or_404` |
| Dependencies with `Depends` | `app/dependencies.py` (shared dict, paging parameters) |
| Background tasks | `app/tasks.py`, used by `create_order` |
| Routers | `APIRouter` in `app/routers/orders.py`, plugged in by `main.py` |

The dependency example in the lesson text reads a bearer token; here the dependencies share the order store and the paging parameters, because authentication is the subject of module M03.

## Endpoints

| Method and path | Description | Success |
| --- | --- | --- |
| `GET /` | Health message | 200 |
| `GET /orders?status=&limit=&offset=` | List order summaries | 200 |
| `GET /orders/{id}` | One order with its lines | 200, 404 |
| `GET /orders/{id}/lines` | The lines of one order | 200, 404 |
| `POST /orders` | Create an order (JSON body, field `orderDate` is an alias) | 201 |
| `PUT /orders/{id}` | Replace an order | 200, 404 |
| `PATCH /orders/{id}` | Change only the sent fields | 200, 404 |
| `DELETE /orders/{id}` | Remove an order | 204, 404 |

Try it:

```bash
curl -s localhost:8000/orders
curl -s -X POST localhost:8000/orders -H 'Content-Type: application/json' \
  -d '{"customer": "Maria Verdi", "orderDate": "2026-03-01", "lines": [{"sku": "PEN-1", "quantity": 4, "unit_price": 2.5}]}'
curl -s -X PATCH localhost:8000/orders/1001 -H 'Content-Type: application/json' -d '{"status": "shipped"}'
```

## Async: what `orders_api_async` shows

The async API has the same operations. Every operation is `async def`, and the fake database call is awaited (`app/slow_io.py`). Three extra endpoints under `/demo` wait for the same time in three different ways, and two overview endpoints need two independent slow calls. `python timing_demo.py` (run from `orders_api_async/`) prints, with a 0.2 s wait and 5 simultaneous requests:

| Case | Time |
| --- | --- |
| `async def` + `await asyncio.sleep` | 0.21 s |
| `def` + `time.sleep` (runs in a thread pool) | 0.21 s |
| `async def` + `time.sleep` (blocks the event loop) | 1.01 s |
| One request: two awaits one after the other | 0.40 s |
| One request: `asyncio.gather` on the same two calls | 0.20 s |

Rules of thumb:

- Use `async def` when the operation awaits async libraries (an async database driver, `httpx.AsyncClient`).
- Use plain `def` when it calls blocking libraries: FastAPI runs it in a thread pool.
- Never call blocking code inside `async def`.
- Async does not make CPU-bound work faster.

The numbers come from sleeping, not from real I/O, and from in-process calls; they show the mechanism, not production performance. The tests compare timings with each other, not with fixed numbers.
