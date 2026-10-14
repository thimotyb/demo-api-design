"""Orders API, module M02 (FastAPI core concepts): the synchronous version.

Run it from the orders_api folder:

    uvicorn app.main:app --reload

then open  http://127.0.0.1:8000/docs  for the interactive documentation.
"""

from contextlib import asynccontextmanager
from itertools import count

from fastapi import FastAPI

from app.routers import orders
from app.store import seed


# ---------------------------------------------------------------------------
# Lifespan: code that runs once at startup and once at shutdown
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- STARTUP: runs once, before the first request ---
    app.state.orders = {}                 # all orders, by id
    app.state.order_ids = count(1001)     # generator of ids: 1001, 1002, 1003, ...
    app.state.outbox = []                 # "sent" confirmation e-mails (see tasks.py)
    seed(app.state.orders, app.state.order_ids)

    yield                                 # <-- the application serves requests here

    # --- SHUTDOWN: runs once, when the server stops ---
    app.state.orders.clear()


# ---------------------------------------------------------------------------
# The application
# ---------------------------------------------------------------------------

# title and description appear in the generated documentation (/docs).
app = FastAPI(
    title="Orders API",
    description="Module M02 example: path operations, parameters, models, dependencies, "
                "background tasks and routers.",
    lifespan=lifespan,
)

# Plug the router in: all /orders operations become part of the application.
app.include_router(orders.router)


# The simplest path operation: GET / returns a small JSON object.
# FastAPI turns the returned dict into JSON automatically.
@app.get("/")
def root():
    return {"message": "Orders API"}
