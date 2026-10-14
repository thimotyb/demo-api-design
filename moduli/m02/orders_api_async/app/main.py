"""Orders API, module M02: the ASYNCHRONOUS version.

Same API as ../orders_api, rewritten with async/await, plus a few endpoints that
make the effect of async visible. Run it from the orders_api_async folder:

    uvicorn app.main:app --reload

then open  http://127.0.0.1:8000/docs
"""

from contextlib import asynccontextmanager
from itertools import count

from fastapi import FastAPI

from app.routers import concurrency, orders
from app.store import seed


@asynccontextmanager
async def lifespan(app: FastAPI):
    # STARTUP: same as the synchronous version.
    app.state.orders = {}
    app.state.order_ids = count(1001)
    app.state.outbox = []
    seed(app.state.orders, app.state.order_ids)

    yield

    # SHUTDOWN
    app.state.orders.clear()


app = FastAPI(
    title="Orders API (async)",
    description="Module M02 example: the Orders API with async/await.",
    lifespan=lifespan,
)

app.include_router(orders.router)
app.include_router(concurrency.router)


# "async def" is the only change needed for the simplest operation too.
@app.get("/")
async def root():
    return {"message": "Orders API (async)"}
