"""The /orders operations, async version.

The code is the same as the synchronous version with two differences:
  1. every path operation is declared with "async def";
  2. the slow parts (the fake database and service calls) are awaited.

"await" means: "start this slow operation and, while it is waiting, let the
server work on other requests". When the operation is done, this function
continues from the same line.
"""

import asyncio

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request

from app import slow_io
from app.dependencies import get_orders, pagination
from app.models import OrderCreate, OrderDetail, OrderLine, OrderPatch, OrderSummary
from app.store import build_order
from app.tasks import send_confirmation

router = APIRouter(prefix="/orders", tags=["Orders"])


async def get_order_or_404(orders: dict, order_id: int) -> OrderDetail:
    """Look an order up (with a fake database call), or answer HTTP 404."""
    await slow_io.database_call()               # waiting for the "database"
    order = orders.get(order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="Order not found")
    return order


@router.get("", response_model=list[OrderSummary])
async def list_orders(
    status: str | None = None,
    page: dict = Depends(pagination),
    orders: dict = Depends(get_orders),
):
    await slow_io.database_call()
    result = list(orders.values())
    if status is not None:
        result = [order for order in result if order.status == status]
    return result[page["offset"] : page["offset"] + page["limit"]]


@router.get("/{order_id}", response_model=OrderDetail)
async def get_order(order_id: int, orders: dict = Depends(get_orders)):
    return await get_order_or_404(orders, order_id)


@router.get("/{order_id}/lines", response_model=list[OrderLine])
async def list_order_lines(order_id: int, orders: dict = Depends(get_orders)):
    return (await get_order_or_404(orders, order_id)).lines


@router.post("", response_model=OrderDetail, status_code=201)
async def create_order(
    data: OrderCreate,
    background: BackgroundTasks,
    request: Request,
    orders: dict = Depends(get_orders),
):
    await slow_io.database_call()               # writing to the "database"
    order_id = next(request.app.state.order_ids)
    orders[order_id] = build_order(order_id, data)
    background.add_task(send_confirmation, request.app.state.outbox, order_id)
    return orders[order_id]


@router.put("/{order_id}", response_model=OrderDetail)
async def replace_order(order_id: int, data: OrderCreate, orders: dict = Depends(get_orders)):
    await get_order_or_404(orders, order_id)
    orders[order_id] = build_order(order_id, data)
    return orders[order_id]


@router.patch("/{order_id}", response_model=OrderDetail)
async def update_order(order_id: int, changes: OrderPatch, orders: dict = Depends(get_orders)):
    order = await get_order_or_404(orders, order_id)
    orders[order_id] = order.model_copy(update=changes.model_dump(exclude_unset=True))
    return orders[order_id]


@router.delete("/{order_id}", status_code=204)
async def delete_order(order_id: int, orders: dict = Depends(get_orders)):
    await get_order_or_404(orders, order_id)
    del orders[order_id]


# ---------------------------------------------------------------------------
# Where async really pays off: two independent slow calls
# ---------------------------------------------------------------------------
# An "overview" needs the order (fake database) AND a shipping estimate (fake
# external service). Neither call needs the result of the other.

@router.get("/{order_id}/overview-sequential")
async def overview_sequential(order_id: int, orders: dict = Depends(get_orders)):
    """One call after the other: takes about 2 x DELAY."""
    order = await get_order_or_404(orders, order_id)       # waits DELAY
    shipping = await slow_io.shipping_service_call()      # then waits DELAY again
    return {"order": order.id, "customer": order.customer, "shipping": shipping}


@router.get("/{order_id}/overview")
async def overview(order_id: int, orders: dict = Depends(get_orders)):
    """Both calls at the same time with asyncio.gather: takes about 1 x DELAY."""
    # gather() starts both coroutines together and waits until both are done.
    order, shipping = await asyncio.gather(
        get_order_or_404(orders, order_id),
        slow_io.shipping_service_call(),
    )
    return {"order": order.id, "customer": order.customer, "shipping": shipping}
