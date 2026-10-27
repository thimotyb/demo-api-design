"""REST API over the shared checkout domain (FastAPI).

Resources: orders, shipments, payments. Idempotency uses the Idempotency-Key
header. /v1 and /v2 show a breaking change that needs a new version.
"""

from __future__ import annotations

import logging
import time
import uuid
from contextvars import ContextVar
from datetime import datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, FastAPI, Header, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field

from shared import domain
from shared.domain import DomainError, Money, Store

# The identifier of the request being served, readable from any code it calls.
request_id: ContextVar[str] = ContextVar("request_id", default="-")
log = logging.getLogger("api")


class RequestIdFilter(logging.Filter):
    """Adds the current request id to every record, so a format can print %(request_id)s."""

    def filter(self, record: logging.LogRecord) -> bool:
        if not hasattr(record, "request_id"):  # a caller may pass it with extra=
            record.request_id = request_id.get()
        return True


log.addFilter(RequestIdFilter())

# Domain error code -> HTTP status. The payment statuses follow the case contract.
STATUS = {
    "INVALID_REQUEST": 400,
    "ORDER_NOT_FOUND": 404,
    "SHIPMENT_NOT_FOUND": 404,
    "CUSTOMER_NOT_FOUND": 404,
    "PAYMENT_DECLINED": 402,
    "TRANSIENT_GATEWAY_FAILURE": 402,
    "RETRIES_EXHAUSTED": 402,
    "IDEMPOTENCY_CONFLICT": 409,
}


class MoneyModel(BaseModel):
    amount: Decimal = Field(gt=0, decimal_places=2)
    currency: str = Field(min_length=3, max_length=3)


class LineOut(BaseModel):
    sku: str
    description: str
    quantity: int
    unit_price: MoneyModel


class OrderV1(BaseModel):
    """v1 exposes the total as two flat fields."""
    id: str
    customer_id: str
    status: str
    total_amount: Decimal
    currency: str
    lines: list[LineOut]
    payment_id: str
    tracking_code: str
    created_at: datetime


class OrderV2(BaseModel):
    """v2 replaces total_amount and currency with a nested money object: a breaking change."""
    id: str
    customer_id: str
    status: str
    total: MoneyModel
    lines: list[LineOut]
    payment_id: str
    tracking_code: str
    created_at: datetime


class EventOut(BaseModel):
    status: str
    location: str
    occurred_at: datetime


class ShipmentOut(BaseModel):
    tracking_code: str
    carrier: str
    status: str
    events: list[EventOut]


class CustomerOut(BaseModel):
    id: str
    email: str
    addresses: list[str]


class PaymentRequest(BaseModel):
    # A payment is sensitive: a misspelled or unexpected field is rejected (400), not ignored.
    model_config = ConfigDict(extra="forbid")

    customer_id: str
    amount: MoneyModel
    payment_token: str


class PaymentOut(BaseModel):
    id: str
    customer_id: str
    amount: MoneyModel
    status: str
    authorization_code: str


class ErrorOut(BaseModel):
    code: str
    message: str
    details: dict = {}


def _lines(order: domain.Order) -> list[LineOut]:
    return [LineOut(sku=l.sku, description=l.description, quantity=l.quantity,
                    unit_price=MoneyModel(amount=l.unit_price.amount, currency=l.unit_price.currency))
            for l in order.lines]


def create_app(store: Store | None = None) -> FastAPI:
    store = store or Store()
    app = FastAPI(title="Checkout REST API")
    app.state.store = store

    @app.middleware("http")
    async def tracing(request: Request, call_next):
        # Accept the caller's X-Request-ID or generate one, and return it in the response.
        rid = request.headers.get("x-request-id", str(uuid.uuid4()))
        token = request_id.set(rid)
        request.state.request_id = rid  # still readable by the handlers, outside the middleware
        started = time.perf_counter()
        status = 500  # what the client gets if an exception escapes every handler
        try:
            response = await call_next(request)
            status = response.status_code
        finally:
            # Method, path, status and duration only: never headers, bodies or tokens.
            log.info("%s %s -> %s in %.1f ms", request.method, request.url.path, status,
                     (time.perf_counter() - started) * 1000)
            request_id.reset(token)
        response.headers["X-Request-ID"] = rid
        return response

    def get_store(request: Request) -> Store:
        return request.app.state.store

    @app.exception_handler(DomainError)
    async def domain_error(request: Request, exc: DomainError):
        return JSONResponse({"code": exc.code, "message": exc.message, "details": exc.details},
                            status_code=STATUS.get(exc.code, 500))

    @app.exception_handler(Exception)
    async def unhandled_error(request: Request, exc: Exception):
        # Last resort, for what no other handler claims. The traceback goes to the log
        # only; the client gets the shared error shape and the id to quote to support.
        rid = getattr(request.state, "request_id", "-")
        log.error("Unhandled error", exc_info=exc, extra={"request_id": rid})
        return JSONResponse({"code": "INTERNAL_ERROR", "message": "Unexpected error.", "details": {}},
                            status_code=500, headers={"X-Request-ID": rid})

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError):
        # Same error shape as every other failure, and the 400 of the case contract.
        first = exc.errors()[0]
        where = ".".join(str(p) for p in first["loc"])
        return JSONResponse({"code": "INVALID_REQUEST", "message": f"{where}: {first['msg']}",
                             "details": {"field": where}}, status_code=400)

    shipments = APIRouter(tags=["Shipments"])

    @shipments.get("/orders/{order_id}/shipment", response_model=ShipmentOut, responses={404: {"model": ErrorOut}})
    def get_shipment(order_id: str, response: Response, s: Store = Depends(get_store)):
        shipment = s.get_shipment_for_order(order_id)
        # Every operation has its own URL and method, so plain HTTP caching applies: a browser,
        # a proxy or a CDN can reuse this response without any application code.
        response.headers["Cache-Control"] = "private, max-age=30"
        return ShipmentOut(tracking_code=shipment.tracking_code, carrier=shipment.carrier, status=shipment.status,
                           events=[EventOut(status=e.status, location=e.location, occurred_at=e.occurred_at)
                                   for e in shipment.events])

    customers = APIRouter(tags=["Customers"])

    @customers.get("/customers/{customer_id}", response_model=CustomerOut, responses={404: {"model": ErrorOut}})
    def get_customer(customer_id: str, s: Store = Depends(get_store)):
        c = s.get_customer(customer_id)
        return CustomerOut(id=c.id, email=c.email, addresses=list(c.addresses))

    v1 = APIRouter(prefix="/v1", tags=["v1"])
    v2 = APIRouter(prefix="/v2", tags=["v2"])
    for router in (v1, v2):
        router.include_router(shipments)

    @v1.get("/orders/{order_id}", response_model=OrderV1, responses={404: {"model": ErrorOut}})
    def get_order_v1(order_id: str, s: Store = Depends(get_store)):
        o = s.get_order(order_id)
        return OrderV1(id=o.id, customer_id=o.customer_id, status=o.status, total_amount=o.total.amount,
                       currency=o.total.currency, lines=_lines(o), payment_id=o.payment_id,
                       tracking_code=o.tracking_code, created_at=o.created_at)

    @v2.get("/orders/{order_id}", response_model=OrderV2, responses={404: {"model": ErrorOut}})
    def get_order_v2(order_id: str, s: Store = Depends(get_store)):
        o = s.get_order(order_id)
        return OrderV2(id=o.id, customer_id=o.customer_id, status=o.status,
                       total=MoneyModel(amount=o.total.amount, currency=o.total.currency), lines=_lines(o),
                       payment_id=o.payment_id, tracking_code=o.tracking_code, created_at=o.created_at)

    @v1.post("/payments", response_model=PaymentOut, status_code=201,
             responses={200: {"model": PaymentOut, "description": "Replay of an earlier request with the same key"},
                        402: {"model": ErrorOut}, 409: {"model": ErrorOut}})
    def authorize_payment(body: PaymentRequest, response: Response, s: Store = Depends(get_store),
                          idempotency_key: str | None = Header(default=None)):
        result = s.authorize_payment(body.customer_id, Money(body.amount.amount, body.amount.currency),
                                     body.payment_token, idempotency_key)
        if result.replayed:
            response.status_code = 200
            response.headers["Idempotent-Replayed"] = "true"
        p = result.payment
        return PaymentOut(id=p.id, customer_id=p.customer_id,
                          amount=MoneyModel(amount=p.amount.amount, currency=p.amount.currency),
                          status=p.status, authorization_code=p.authorization_code)

    v1.include_router(customers)
    app.include_router(v1)
    app.include_router(v2)
    return app


app = create_app()
