"""In-memory checkout domain shared by the REST, GraphQL and gRPC examples.

All data is synthetic. Each Store is an independent instance, so every test
starts from the same seed data. The payment gateway is simulated: the payment
token selects the outcome.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from itertools import count
import re


# --- Errors -----------------------------------------------------------------
# Every failure carries a stable, machine-readable code. Each API style maps
# the code to its own mechanism (HTTP status, gRPC status, GraphQL extensions).

class DomainError(Exception):
    code = "DOMAIN_ERROR"

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class InvalidRequest(DomainError):
    code = "INVALID_REQUEST"


class OrderNotFound(DomainError):
    code = "ORDER_NOT_FOUND"


class ShipmentNotFound(DomainError):
    code = "SHIPMENT_NOT_FOUND"


class CustomerNotFound(DomainError):
    code = "CUSTOMER_NOT_FOUND"


class PaymentDeclined(DomainError):
    code = "PAYMENT_DECLINED"


class TransientGatewayFailure(DomainError):
    code = "TRANSIENT_GATEWAY_FAILURE"


class IdempotencyConflict(DomainError):
    code = "IDEMPOTENCY_CONFLICT"


# --- Entities ---------------------------------------------------------------

@dataclass(frozen=True)
class Money:
    amount: Decimal
    currency: str


@dataclass(frozen=True)
class OrderLine:
    sku: str
    description: str
    quantity: int
    unit_price: Money


@dataclass(frozen=True)
class ShipmentEvent:
    status: str  # CREATED | IN_TRANSIT | DELIVERED
    location: str
    occurred_at: datetime


@dataclass
class Shipment:
    tracking_code: str
    carrier: str
    events: list[ShipmentEvent] = field(default_factory=list)

    @property
    def status(self) -> str:
        return self.events[-1].status if self.events else "CREATED"


@dataclass(frozen=True)
class Customer:
    id: str
    email: str
    addresses: tuple[str, ...]


@dataclass(frozen=True)
class Payment:
    id: str
    customer_id: str
    amount: Money
    status: str  # AUTHORIZED
    authorization_code: str


@dataclass
class Order:
    id: str
    customer_id: str
    status: str  # NEW | PAID | SHIPPED | DELIVERED | CANCELED
    lines: list[OrderLine]
    payment_id: str
    tracking_code: str
    created_at: datetime

    @property
    def total(self) -> Money:
        currency = self.lines[0].unit_price.currency
        return Money(sum((l.unit_price.amount * l.quantity for l in self.lines), Decimal("0")), currency)


@dataclass(frozen=True)
class PaymentResult:
    payment: Payment
    replayed: bool


# --- Simulated payment gateway ---------------------------------------------

class FakeGateway:
    """The token selects the outcome, so tests and demos are deterministic.

    tok_demo_visa  approved
    tok_declined   definitive refusal
    tok_transient  transient failure on every call
    tok_flaky      transient failure on the first call, approved afterwards
    """

    def __init__(self) -> None:
        self.calls = 0
        self._flaky_seen = False

    def authorize(self, amount: Money, token: str) -> str:
        # Count every call, including failed ones: tests use `calls` to check
        # whether the gateway was really contacted (e.g. not on an idempotent replay).
        self.calls += 1

        # Happy path: the payment is approved and we return an authorization code.
        if token == "tok_demo_visa":
            return f"AUTH-{self.calls:04d}"

        # Definitive failure: the bank refused the payment. Retrying will not help,
        # so the API stores this outcome and replays it for the same idempotency key.
        if token == "tok_declined":
            raise PaymentDeclined("Payment declined; do not retry automatically.")

        # Permanent outage: the gateway is "down" and fails on every call. It shows a
        # retryable error that never recovers, whatever the client does.
        if token == "tok_transient":
            raise TransientGatewayFailure("Gateway temporarily unavailable; retry with the same Idempotency-Key.")

        # Recovering outage: fails on the first call only, then works. This simulates
        # a real glitch and lets tests prove that a retry with the same key succeeds.
        if token == "tok_flaky":
            if not self._flaky_seen:
                self._flaky_seen = True
                raise TransientGatewayFailure("Gateway temporarily unavailable; retry with the same Idempotency-Key.")
            return f"AUTH-{self.calls:04d}"

        # Any other token is a client error, not a gateway outcome.
        raise InvalidRequest(f"Unknown payment token: {token}")


# --- Store ------------------------------------------------------------------

_TRACKING = re.compile(r"^TRK-[A-Z0-9]{3,12}$")
T0 = datetime(2026, 1, 1, 10, 0, tzinfo=timezone.utc)


def _at(minutes: int) -> datetime:
    return T0 + timedelta(minutes=minutes)


class Store:
    """Customers, orders, shipments and payments, with idempotent authorization."""

    def __init__(self) -> None:
        self.gateway = FakeGateway()
        self.carrier_lookups = 0  # each get_shipment stands for one call to the carrier
        self.customers: dict[str, Customer] = {}
        self.orders: dict[str, Order] = {}
        self.shipments: dict[str, Shipment] = {}
        self.payments: dict[str, Payment] = {}
        # idempotency key -> (request fingerprint, stored outcome)
        self._idempotency: dict[str, tuple[tuple, Payment | DomainError]] = {}
        self._payment_ids = count(1)
        self._seed()

    def _seed(self) -> None:
        eur = lambda amount: Money(Decimal(amount), "EUR")
        self.customers["c-001"] = Customer("c-001", "anna.rossi@example.com", ("Via Roma 1, Milano", "Via Verdi 7, Torino"))
        self.payments["p-0000"] = Payment("p-0000", "c-001", eur("64.50"), "AUTHORIZED", "AUTH-0000")
        self.orders["o-1001"] = Order(
            "o-1001", "c-001", "SHIPPED",
            [
                OrderLine("SKU-BOOK-1", "API Design handbook", 1, eur("34.50")),
                OrderLine("SKU-MUG-2", "Coffee mug", 2, eur("10.00")),
                OrderLine("SKU-STK-3", "Sticker pack", 1, eur("10.00")),
            ],
            "p-0000", "TRK-1001", T0,
        )
        self.shipments["TRK-1001"] = Shipment("TRK-1001", "Example Carrier", [
            ShipmentEvent("CREATED", "Milano depot", _at(0)),
            ShipmentEvent("IN_TRANSIT", "Bologna hub", _at(30)),
        ])
        # A shipment whose carrier lookup is slow, used to demonstrate deadlines.
        self.shipments["TRK-SLOW"] = Shipment("TRK-SLOW", "Slow Carrier", [ShipmentEvent("CREATED", "Roma depot", _at(0))])

    # -- reads
    def get_order(self, order_id: str) -> Order:
        try:
            return self.orders[order_id]
        except KeyError:
            raise OrderNotFound(f"Order {order_id} does not exist.") from None

    def get_customer(self, customer_id: str) -> Customer:
        try:
            return self.customers[customer_id]
        except KeyError:
            raise CustomerNotFound(f"Customer {customer_id} does not exist.") from None

    def get_shipment(self, tracking_code: str) -> Shipment:
        self.carrier_lookups += 1
        if not _TRACKING.match(tracking_code or ""):
            raise InvalidRequest("Tracking code must look like TRK-1001.")
        try:
            return self.shipments[tracking_code]
        except KeyError:
            raise ShipmentNotFound(f"Shipment {tracking_code} does not exist.") from None

    def get_shipment_for_order(self, order_id: str) -> Shipment:
        return self.get_shipment(self.get_order(order_id).tracking_code)

    def future_events(self, tracking_code: str) -> list[ShipmentEvent]:
        """Scripted carrier updates that a tracking stream emits after the history."""
        shipment = self.get_shipment(tracking_code)
        if shipment.status == "DELIVERED":
            return []
        return [
            ShipmentEvent("IN_TRANSIT", "Firenze hub", _at(75)),
            ShipmentEvent("IN_TRANSIT", "Local depot", _at(120)),
            ShipmentEvent("DELIVERED", "Customer address", _at(150)),
        ]

    # -- commands
    def authorize_payment(self, customer_id: str, amount: Money, token: str,
                          idempotency_key: str | None = None) -> PaymentResult:
        # Step 1 - Validate the input. Invalid requests are rejected first and are
        # never stored against an idempotency key.
        if customer_id not in self.customers:
            raise InvalidRequest(f"Unknown customer {customer_id}.")
        if amount.amount <= 0 or len(amount.currency) != 3:
            raise InvalidRequest("Amount must be positive and currency must be a 3-letter code.")

        # Step 2 - Check the idempotency key. The fingerprint identifies "the same
        # request": if the key was already used, we compare what was sent then and now.
        fingerprint = (customer_id, amount.amount, amount.currency, token)
        if idempotency_key is not None and idempotency_key in self._idempotency:
            stored_fingerprint, outcome = self._idempotency[idempotency_key]
            # Same key but a different request: a client bug, so refuse it (409).
            if stored_fingerprint != fingerprint:
                raise IdempotencyConflict("This Idempotency-Key was already used with a different request.")
            # Same request, and the first attempt ended with a stored refusal:
            # give the same refusal back without calling the gateway again.
            if isinstance(outcome, DomainError):
                raise outcome
            # Same request, and the first attempt succeeded: replay the stored
            # payment instead of charging twice.
            return PaymentResult(outcome, replayed=True)

        # Step 3 - First time we see this request: call the payment gateway.
        try:
            code = self.gateway.authorize(amount, token)
        except TransientGatewayFailure:
            raise  # not stored: the client must be able to retry with the same key
        except DomainError as error:
            # A definitive refusal (e.g. card declined) is remembered, so a retry
            # with the same key gets the same answer. Other errors are not stored.
            if idempotency_key is not None and isinstance(error, PaymentDeclined):
                self._idempotency[idempotency_key] = (fingerprint, error)
            raise

        # Step 4 - Success: create and store the payment, and remember it under the
        # key so that a later retry is recognised as a replay.
        payment = Payment(f"p-{next(self._payment_ids):04d}", customer_id, amount, "AUTHORIZED", code)
        self.payments[payment.id] = payment
        if idempotency_key is not None:
            self._idempotency[idempotency_key] = (fingerprint, payment)
        return PaymentResult(payment, replayed=False)
