"""GraphQL API over the shared checkout domain (Strawberry on FastAPI).

One endpoint, POST /graphql. The client chooses the fields. Failures are
returned with HTTP 200 and an `errors` array whose `extensions.code` carries the
same stable domain codes used by the other styles.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

import strawberry
import time
from collections.abc import Callable

from fastapi import FastAPI, Request, Response
from graphql import GraphQLError
from strawberry.fastapi import GraphQLRouter

from shared import domain
from graphql_api.policies import CachedField, FieldCache, QueryCostLimiter, RateLimitExtension
from shared.domain import DomainError, Store


def api_error(error: DomainError) -> GraphQLError:
    return GraphQLError(error.message, extensions={"code": error.code})


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


def _money(m: domain.Money) -> Money:
    return Money(amount=m.amount, currency=m.currency)


def _shipment(s: domain.Shipment) -> Shipment:
    events = [ShipmentEvent(status=e.status, location=e.location, occurred_at=e.occurred_at) for e in s.events]
    return Shipment(tracking_code=s.tracking_code, carrier=s.carrier, status=s.status,
                    events=events, last_event=events[-1] if events else None)


@strawberry.type
class Order:
    id: str
    status: str
    created_at: datetime
    lines: list[OrderLine]
    payment_id: str
    _domain: strawberry.Private[domain.Order]
    _store: strawberry.Private[Store]

    # The first version exposed the total as two flat fields. The nested `total`
    # was added next to them and the old fields were deprecated: no new version
    # and no broken client.
    @strawberry.field(deprecation_reason="Use total.amount")
    def total_amount(self) -> Decimal:
        return self._domain.total.amount

    @strawberry.field(deprecation_reason="Use total.currency")
    def currency(self) -> str:
        return self._domain.total.currency

    @strawberry.field
    def total(self) -> Money:
        return _money(self._domain.total)

    @strawberry.field
    def customer(self) -> Customer:
        c = self._store.get_customer(self._domain.customer_id)
        return Customer(id=c.id, email=c.email, addresses=list(c.addresses))

    # The carrier lookup is the expensive part of this API. Its result is public
    # carrier data, so it is cached by tracking code for 30 seconds, whoever asks.
    @strawberry.field(extensions=[CachedField(ttl=30, key=lambda source, kwargs: source._domain.tracking_code)])
    def shipment(self) -> Shipment:
        return _shipment(self._store.get_shipment(self._domain.tracking_code))


def _order(o: domain.Order, store: Store) -> Order:
    lines = [OrderLine(sku=l.sku, description=l.description, quantity=l.quantity, unit_price=_money(l.unit_price))
             for l in o.lines]
    return Order(id=o.id, status=o.status, created_at=o.created_at, lines=lines, payment_id=o.payment_id,
                 _domain=o, _store=store)


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
    def order(self, info: strawberry.Info, id: str) -> Order:
        store: Store = info.context["store"]
        try:
            return _order(store.get_order(id), store)
        except DomainError as error:
            raise api_error(error) from error


@strawberry.type
class Mutation:
    @strawberry.mutation
    def authorize_payment(self, info: strawberry.Info, input: AuthorizePaymentInput) -> Payment:
        store: Store = info.context["store"]
        try:
            result = store.authorize_payment(input.customer_id, domain.Money(input.amount.amount, input.amount.currency),
                                             input.payment_token, input.idempotency_key)
        except DomainError as error:
            raise api_error(error) from error
        p = result.payment
        return Payment(id=p.id, amount=_money(p.amount), status=p.status,
                       authorization_code=p.authorization_code, replayed=result.replayed)


schema = strawberry.Schema(query=Query, mutation=Mutation, extensions=[RateLimitExtension])


def create_app(store: Store | None = None, clock: Callable[[], float] = time.monotonic,
               capacity: float = 20, refill_per_second: float = 10) -> FastAPI:
    store = store or Store()
    cache = FieldCache(clock=clock)
    limiter = QueryCostLimiter(capacity=capacity, refill_per_second=refill_per_second, clock=clock)

    async def context(request: Request, response: Response) -> dict:
        client = request.headers.get("x-client-id") or (request.client.host if request.client else "anonymous")
        return {"store": store, "cache": cache, "limiter": limiter, "client": client, "response": response}

    app = FastAPI(title="Checkout GraphQL API")
    app.state.store = store
    app.include_router(GraphQLRouter(schema, context_getter=context), prefix="/graphql")
    return app


app = create_app()
