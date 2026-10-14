"""Dependencies, as in the synchronous version.

A dependency can be a normal function ("def") or a coroutine ("async def").
FastAPI accepts both:
  * "def" dependencies run in a thread pool, so they can block safely;
  * "async def" dependencies run directly on the event loop, so they must never block.
"""

from fastapi import Query, Request


async def get_orders(request: Request) -> dict:
    """Give the operation the dict that holds all orders (async dependency)."""
    return request.app.state.orders


def pagination(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> dict:
    """Common paging parameters (a plain "def" dependency: it does no waiting)."""
    return {"limit": limit, "offset": offset}
