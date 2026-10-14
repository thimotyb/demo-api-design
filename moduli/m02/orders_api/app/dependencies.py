"""Dependencies: small functions that FastAPI runs *before* a path operation.

A path operation asks for one with  Depends(function).  FastAPI calls the
function, reads its parameters from the request (query string, headers, ...),
and passes the returned value to the path operation.

Use dependencies for anything shared by several operations.
Authentication will be added the same way in module M03.
"""

from fastapi import Query, Request


def get_orders(request: Request) -> dict:
    """Give the operation the dict that holds all orders.

    The dict is created once at startup (see lifespan in main.py) and stored on
    app.state, so every request sees the same data.
    """
    return request.app.state.orders


def pagination(
    limit: int = Query(20, ge=1, le=100),   # query parameter ?limit=..., between 1 and 100
    offset: int = Query(0, ge=0),           # query parameter ?offset=...
) -> dict:
    """Common paging parameters, reusable by any list endpoint."""
    return {"limit": limit, "offset": offset}
