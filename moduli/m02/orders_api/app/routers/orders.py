"""The /orders operations: GET, POST, PUT, PATCH and DELETE.

An APIRouter groups related operations (same prefix, same tag) in their own
module. main.py plugs the router into the application with include_router().
"""

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request

from app.dependencies import get_orders, pagination
from app.models import OrderCreate, OrderDetail, OrderLine, OrderPatch, OrderSummary
from app.store import build_order
from app.tasks import send_confirmation

# prefix: every path below starts with /orders.
# tags:   groups the operations under "Orders" in the /docs page.
router = APIRouter(prefix="/orders", tags=["Orders"])


def get_order_or_404(orders: dict, order_id: int) -> OrderDetail:
    """Look an order up, or answer HTTP 404 if it does not exist."""
    order = orders.get(order_id)
    if order is None:
        # Raising HTTPException stops the operation and sends this status code.
        raise HTTPException(status_code=404, detail="Order not found")
    return order


# ---------------------------------------------------------------------------
# GET: read
# ---------------------------------------------------------------------------

# response_model=list[OrderSummary] filters the output: even though we return full
# orders, the client only receives the summary fields (no lines).
@router.get("", response_model=list[OrderSummary])
def list_orders(
    status: str | None = None,                  # simple type, not in the path -> query parameter ?status=
    page: dict = Depends(pagination),           # ?limit= and ?offset= come from a dependency
    orders: dict = Depends(get_orders),         # the shared dict of orders
):
    """List orders, optionally filtered by status, with paging."""
    result = list(orders.values())
    if status is not None:
        result = [order for order in result if order.status == status]
    return result[page["offset"] : page["offset"] + page["limit"]]


# {order_id} is a PATH parameter. The annotation "int" makes FastAPI convert it
# and answer 422 if the value is not a number (for example /orders/abc).
@router.get("/{order_id}", response_model=OrderDetail)
def get_order(order_id: int, orders: dict = Depends(get_orders)):
    """Return one order with all its lines."""
    return get_order_or_404(orders, order_id)


@router.get("/{order_id}/lines", response_model=list[OrderLine])
def list_order_lines(order_id: int, orders: dict = Depends(get_orders)):
    """Return only the lines of one order."""
    return get_order_or_404(orders, order_id).lines


# ---------------------------------------------------------------------------
# POST: create
# ---------------------------------------------------------------------------

# status_code=201 means "Created". Without it FastAPI would answer 200.
@router.post("", response_model=OrderDetail, status_code=201)
def create_order(
    data: OrderCreate,                          # a Pydantic model -> read from the JSON BODY
    background: BackgroundTasks,                # FastAPI gives us an object to schedule tasks
    request: Request,
    orders: dict = Depends(get_orders),
):
    """Create a new order from the JSON body."""
    order_id = next(request.app.state.order_ids)          # next free id: 1003, 1004, ...
    order = build_order(order_id, data)
    orders[order_id] = order

    # Run send_confirmation AFTER the response has been sent.
    background.add_task(send_confirmation, request.app.state.outbox, order_id)
    return order


# ---------------------------------------------------------------------------
# PUT: replace
# ---------------------------------------------------------------------------

@router.put("/{order_id}", response_model=OrderDetail)
def replace_order(order_id: int, data: OrderCreate, orders: dict = Depends(get_orders)):
    """Replace an order completely with the body. The id stays the same."""
    get_order_or_404(orders, order_id)          # 404 if it does not exist
    orders[order_id] = build_order(order_id, data)
    return orders[order_id]


# ---------------------------------------------------------------------------
# PATCH: partial update
# ---------------------------------------------------------------------------

@router.patch("/{order_id}", response_model=OrderDetail)
def update_order(order_id: int, changes: OrderPatch, orders: dict = Depends(get_orders)):
    """Change only the fields present in the body (for example just the status)."""
    order = get_order_or_404(orders, order_id)
    # exclude_unset=True keeps only the fields the client actually sent.
    updated = order.model_copy(update=changes.model_dump(exclude_unset=True))
    orders[order_id] = updated
    return updated


# ---------------------------------------------------------------------------
# DELETE: remove
# ---------------------------------------------------------------------------

# 204 means "No Content": success, and nothing to send back.
@router.delete("/{order_id}", status_code=204)
def delete_order(order_id: int, orders: dict = Depends(get_orders)):
    """Remove an order."""
    get_order_or_404(orders, order_id)
    del orders[order_id]
