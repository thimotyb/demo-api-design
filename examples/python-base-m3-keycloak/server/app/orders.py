from collections.abc import Sequence
from datetime import date
from itertools import count

from fastapi import HTTPException, status
from pydantic import BaseModel, Field


# Base schema for a single order line as it arrives from the client.
class OrderLineBase(BaseModel):
    sku: str = Field(..., min_length=1)
    description: str = Field(..., min_length=1)
    quantity: int = Field(..., ge=1)
    unit_price: float = Field(..., ge=0)


# Stored line representation with a generated identifier.
class OrderLine(OrderLineBase):
    id: int


# Payload used to create a new order with header data plus rows.
class OrderCreate(BaseModel):
    customer: str = Field(..., min_length=1)
    order_date: date = Field(default_factory=date.today)
    status: str = Field(default="new", min_length=1)
    lines: list[OrderLineBase] = Field(default_factory=list)


# Summary view returned by list endpoints.
class OrderSummary(BaseModel):
    id: int
    customer: str
    order_date: date
    status: str
    line_count: int
    total_amount: float


# Full order representation including all lines.
class OrderDetail(OrderSummary):
    lines: list[OrderLine]


# In-memory counters used to generate simple demo ids.
_order_ids = count(1001)
_line_ids = count(1)
# In-memory repository used only for the local example.
_orders: dict[int, OrderDetail] = {}


def total_amount(lines: Sequence[OrderLineBase | OrderLine]) -> float:
    # Sum quantity * unit price for each row and round like a money value.
    return round(sum(line.quantity * line.unit_price for line in lines), 2)


def summary(order: OrderDetail) -> OrderSummary:
    # Project the full order down to the fields shown in the list view.
    return OrderSummary(
        id=order.id,
        customer=order.customer,
        order_date=order.order_date,
        status=order.status,
        line_count=len(order.lines),
        total_amount=total_amount(order.lines),
    )


def create_order_record(payload: OrderCreate) -> OrderDetail:
    # Convert the incoming payload into a stored order with generated ids for the order and each row.
    order_id = next(_order_ids)
    lines = [
        OrderLine(id=next(_line_ids), **line.model_dump())
        for line in payload.lines
    ]
    order = OrderDetail(
        id=order_id,
        customer=payload.customer,
        order_date=payload.order_date,
        status=payload.status,
        lines=lines,
        line_count=len(lines),
        total_amount=total_amount(lines),
    )
    _orders[order_id] = order
    return order


def get_order_or_404(order_id: int) -> OrderDetail:
    # Keep the API behavior explicit: unknown ids become a 404 response.
    order = _orders.get(order_id)
    if order is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Order {order_id} not found",
        )
    return order


def list_orders() -> list[OrderSummary]:
    # Return only the order header summary for the list endpoint.
    return [summary(order) for order in _orders.values()]


def seed_orders() -> None:
    # Keep a couple of records available so the client can read data immediately after startup.
    if _orders:
        return

    create_order_record(
        OrderCreate(
            customer="Acme SRL",
            order_date=date(2026, 5, 10),
            status="confirmed",
            lines=[
                OrderLineBase(sku="PEN-001", description="Blue pen", quantity=10, unit_price=1.2),
                OrderLineBase(sku="NBK-010", description="Notebook A4", quantity=5, unit_price=3.5),
            ],
        )
    )
    create_order_record(
        OrderCreate(
            customer="Beta Spa",
            order_date=date(2026, 5, 12),
            status="draft",
            lines=[
                OrderLineBase(sku="USB-128", description="USB drive 128GB", quantity=2, unit_price=12.0),
            ],
        )
    )
