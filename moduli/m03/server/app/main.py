from fastapi import Depends, FastAPI, Header, HTTPException, status

from .auth import decode_access_token
from .orders import (
    OrderCreate,
    OrderDetail,
    OrderLine,
    OrderSummary,
    create_order_record,
    get_order_or_404,
    list_orders as get_order_summaries,
    seed_orders,
)

app = FastAPI(title="M3 Orders API demo")

seed_orders()


def require_bearer_token(authorization: str = Header(default="")) -> dict:
    # FastAPI injects the Authorization header here; reject anything that is not a Bearer token.
    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = authorization.removeprefix("Bearer ").strip()
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return decode_access_token(token)


@app.get("/")
def root() -> dict:
    # Unprotected endpoint used to check that the API is up.
    return {"message": "M3 Orders API demo"}


@app.get("/orders", response_model=list[OrderSummary])
def list_orders(_payload: dict = Depends(require_bearer_token)) -> list[OrderSummary]:
    # Protected list endpoint: return headers only, so the client can inspect the order summary table.
    return get_order_summaries()


@app.get("/orders/{order_id}", response_model=OrderDetail)
def get_order(order_id: int, _payload: dict = Depends(require_bearer_token)) -> OrderDetail:
    # Protected detail endpoint: return the order header plus all rows.
    return get_order_or_404(order_id)


@app.get("/orders/{order_id}/lines", response_model=list[OrderLine])
def list_order_lines(order_id: int, _payload: dict = Depends(require_bearer_token)) -> list[OrderLine]:
    # Convenience endpoint for the client when it wants to focus only on the order rows.
    return get_order_or_404(order_id).lines


@app.post("/orders", response_model=OrderDetail, status_code=status.HTTP_201_CREATED)
def create_order(order: OrderCreate, _payload: dict = Depends(require_bearer_token)) -> OrderDetail:
    # Create a new order in memory and return the stored representation with generated ids.
    return create_order_record(order)
