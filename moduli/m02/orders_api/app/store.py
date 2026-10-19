"""A tiny in-memory "database": plain functions that build and store orders.

Everything is kept in a dict, so data is lost when the server stops.
That is enough to learn FastAPI; a real service would use a database.
"""

from app.models import OrderCreate, OrderDetail, OrderLine, OrderLineIn


def build_order(order_id: int, data: OrderCreate) -> OrderDetail:
    """Turn the client's OrderCreate into a stored OrderDetail."""
    # Give each line a sequential id (1, 2, 3, ...).
    lines = [
        OrderLine(id=index, **line.model_dump())
        for index, line in enumerate(data.lines, start=1)
    ]
    total = round(sum(line.quantity * line.unit_price for line in lines), 2)
    # type: ignore: the type checker only sees the alias "orderDate" as a constructor
    # argument, but populate_by_name=True makes order_date valid at runtime.
    return OrderDetail(  # type: ignore[call-arg]
        id=order_id,
        customer=data.customer,
        order_date=data.order_date,  # type: ignore[call-arg]
        status=data.status,
        line_count=len(lines),
        total_amount=total,
        lines=lines,
    )


def seed(orders: dict, next_id) -> None:
    """Put two example orders in the store so the API is not empty at startup."""
    examples = [
        OrderCreate(
            customer="Anna Rossi",
            status="paid",
            lines=[ 
                OrderLineIn(sku="BOOK-1", description="API Design handbook", quantity=1, unit_price=34.5),
                OrderLineIn(sku="MUG-2", description="Coffee mug", quantity=2, unit_price=10),
            ],
        ),
        OrderCreate( 
            customer="Luca Bianchi", 
            lines=[OrderLineIn(sku="STK-3", description="Sticker pack", quantity=3, unit_price=4)],
        ),
    ]
    for example in examples:
        order_id = next(next_id)
        orders[order_id] = build_order(order_id, example)
