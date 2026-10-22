"""GraphQL API over the REST checkout API (Strawberry on FastAPI).

One endpoint, POST /graphql. The client chooses the fields. The server holds no
data: it is a backend-for-frontend whose resolvers call the REST API over HTTP
(`/v2/orders/{id}`, `/v1/orders/{id}/shipment`, `/v1/customers/{id}`,
`/v1/payments`), so it neither reads the store nor repeats the domain rules.
Failures are returned with HTTP 200 and an `errors` array whose
`extensions.code` carries the stable code found in the REST error body.
"""

from __future__ import annotations

import os
import time
from collections.abc import Callable
from contextlib import asynccontextmanager
from datetime import datetime
from decimal import Decimal

import httpx
import strawberry
from fastapi import FastAPI, Request, Response
from graphql import GraphQLError
from strawberry.fastapi import GraphQLRouter

from graphql_api.policies import CachedField, FieldCache, QueryCostLimiter, RateLimitExtension

REST_API_URL = os.environ.get("REST_API_URL", "http://127.0.0.1:8000")


def rest_client(app=None, base_url: str = REST_API_URL) -> httpx.AsyncClient:
    """HTTP client for the REST API; with `app`, the calls go to that ASGI app in-process (tests)."""
    if app is not None:
        return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://rest")
    return httpx.AsyncClient(base_url=base_url, timeout=5)


async def call_rest(info: strawberry.Info, method: str, path: str, **kwargs) -> httpx.Response:
    """Call the REST API and turn an error response into a GraphQL error with the same code."""
    try:
        response = await info.context["rest"].request(method, path, **kwargs)
    except httpx.TransportError as error:
        raise GraphQLError("The REST API is unreachable.", extensions={"code": "UPSTREAM_UNAVAILABLE"}) from error
    if response.is_success:
        return response
    try:
        body = response.json()
    except ValueError:
        body = {}
    raise GraphQLError(body.get("message", "Unexpected response from the REST API."),
                       extensions={"code": body.get("code", "UPSTREAM_ERROR")})


def _time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


@strawberry.type
class Money:
    amount: Decimal
    currency: str


@strawberry.type
class OrderLine:
    sku: str
    description: str
    quantity: int
    unit_price: Money


@strawberry.type
class ShipmentEvent:
    status: str
    location: str
    occurred_at: datetime


@strawberry.type
class Shipment:
    tracking_code: str
    carrier: str
    status: str
    events: list[ShipmentEvent]
    last_event: ShipmentEvent | None


@strawberry.type
class Customer:
    id: str
    email: str
    addresses: list[str]


@strawberry.type
class Payment:
    id: str
    amount: Money
    status: str
    authorization_code: str
    replayed: bool


def _money(m: dict) -> Money:
    return Money(amount=Decimal(m["amount"]), currency=m["currency"])


def _shipment(s: dict) -> Shipment:
    events = [ShipmentEvent(status=e["status"], location=e["location"], occurred_at=_time(e["occurred_at"]))
              for e in s["events"]]
    return Shipment(tracking_code=s["tracking_code"], carrier=s["carrier"], status=s["status"],
                    events=events, last_event=events[-1] if events else None)


@strawberry.type
class Order:
    id: str
    status: str
    created_at: datetime
    lines: list[OrderLine]
    payment_id: str
    _data: strawberry.Private[dict]

    # The first version exposed the total as two flat fields. The nested `total`
    # was added next to them and the old fields were deprecated: no new version
    # and no broken client.
    @strawberry.field(deprecation_reason="Use total.amount")
    def total_amount(self) -> Decimal:
        return Decimal(self._data["total"]["amount"])

    @strawberry.field(deprecation_reason="Use total.currency")
    def currency(self) -> str:
        return self._data["total"]["currency"]

    @strawberry.field
    def total(self) -> Money:
        return _money(self._data["total"])

    # One more REST call, made only when the query selects `customer`.
    @strawberry.field
    async def customer(self, info: strawberry.Info) -> Customer:
        c = (await call_rest(info, "GET", f"/v1/customers/{self._data['customer_id']}")).json()
        return Customer(id=c["id"], email=c["email"], addresses=c["addresses"])

    # The carrier lookup is the expensive part of this API. Its result is public
    # carrier data, so it is cached by tracking code for 30 seconds, whoever asks.
    @strawberry.field(extensions=[CachedField(ttl=30, key=lambda source, kwargs: source._data["tracking_code"])])
    async def shipment(self, info: strawberry.Info) -> Shipment:
        response = await call_rest(info, "GET", f"/v1/orders/{self._data['id']}/shipment")
        return _shipment(response.json())


def _order(o: dict) -> Order:
    lines = [OrderLine(sku=l["sku"], description=l["description"], quantity=l["quantity"],
                       unit_price=_money(l["unit_price"])) for l in o["lines"]]
    return Order(id=o["id"], status=o["status"], created_at=_time(o["created_at"]), lines=lines,
                 payment_id=o["payment_id"], _data=o)


@strawberry.input
class MoneyInput:
    amount: Decimal
    currency: str


@strawberry.input
class AuthorizePaymentInput:
    customer_id: str
    amount: MoneyInput
    payment_token: str
    idempotency_key: str | None = None


@strawberry.type
class Query:
    @strawberry.field
    async def order(self, info: strawberry.Info, id: str) -> Order:
        return _order((await call_rest(info, "GET", f"/v2/orders/{id}")).json())


@strawberry.type
class Mutation:
    @strawberry.mutation
    async def authorize_payment(self, info: strawberry.Info, input: AuthorizePaymentInput) -> Payment:
        body = {"customer_id": input.customer_id,
                "amount": {"amount": str(input.amount.amount), "currency": input.amount.currency},
                "payment_token": input.payment_token}
        # The GraphQL input field becomes the REST header: the REST API owns idempotency.
        headers = {"Idempotency-Key": input.idempotency_key} if input.idempotency_key else {}
        response = await call_rest(info, "POST", "/v1/payments", json=body, headers=headers)
        p = response.json()
        return Payment(id=p["id"], amount=_money(p["amount"]), status=p["status"],
                       authorization_code=p["authorization_code"],
                       replayed=response.headers.get("Idempotent-Replayed") == "true")


schema = strawberry.Schema(query=Query, mutation=Mutation, extensions=[RateLimitExtension])


def create_app(rest: httpx.AsyncClient | None = None, clock: Callable[[], float] = time.monotonic,
               capacity: float = 20, refill_per_second: float = 10) -> FastAPI:
    rest = rest or rest_client()
    cache = FieldCache(clock=clock)
    limiter = QueryCostLimiter(capacity=capacity, refill_per_second=refill_per_second, clock=clock)

    async def context(request: Request, response: Response) -> dict:
        client = request.headers.get("x-client-id") or (request.client.host if request.client else "anonymous")
        return {"rest": rest, "cache": cache, "limiter": limiter, "client": client, "response": response}

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        yield
        await rest.aclose()

    app = FastAPI(title="Checkout GraphQL API", lifespan=lifespan)
    app.include_router(GraphQLRouter(schema, context_getter=context), prefix="/graphql")
    return app


app = create_app()
