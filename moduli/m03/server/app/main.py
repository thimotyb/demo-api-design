from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.openapi.models import OAuthFlowClientCredentials, OAuthFlows
from fastapi.security import OAuth2

from .auth import decode_access_token, get_settings, token_roles
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


# Declares the OAuth2 client credentials flow in the OpenAPI document. This is what makes the
# Authorize button appear in /docs and lets generators know how the API is protected.
# auto_error=False: the scheme only reads the Authorization header, and the checks below give
# the 401 answers.
oauth2_scheme = OAuth2(
    flows=OAuthFlows(clientCredentials=OAuthFlowClientCredentials(tokenUrl=get_settings()["token_url"])),
    scheme_name="OAuth2ClientCredentials",
    description="Client credentials flow of the Keycloak realm m3-jwt",
    auto_error=False,
)

PROTECTED = {
    401: {"description": "Missing or invalid bearer token"},
    403: {"description": "Valid token without the required role"},
}


def require_bearer_token(authorization: str | None = Depends(oauth2_scheme)) -> dict:
    # The scheme hands over the raw Authorization header; reject anything that is not a Bearer token.
    if not authorization or not authorization.startswith("Bearer "):
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


def require_role(role: str):
    # Authentication says who the caller is; the role says what the caller may do.
    # A valid token without the role gets 403 (401 is only for a missing or invalid token).
    def checker(payload: dict = Depends(require_bearer_token)) -> dict:
        if role not in token_roles(payload):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions: role {role} required",
            )
        return payload

    return checker


@app.get("/")
def root() -> dict:
    # Unprotected endpoint used to check that the API is up.
    return {"message": "M3 Orders API demo"}


@app.get("/orders", response_model=list[OrderSummary], responses=PROTECTED)
def list_orders(_payload: dict = Depends(require_role("orders:read"))) -> list[OrderSummary]:
    # Protected list endpoint: return headers only, so the client can inspect the order summary table.
    return get_order_summaries()


@app.get("/orders/{order_id}", response_model=OrderDetail, responses=PROTECTED)
def get_order(order_id: int, _payload: dict = Depends(require_role("orders:read"))) -> OrderDetail:
    # Protected detail endpoint: return the order header plus all rows.
    return get_order_or_404(order_id)


@app.get("/orders/{order_id}/lines", response_model=list[OrderLine], responses=PROTECTED)
def list_order_lines(order_id: int, _payload: dict = Depends(require_role("orders:read"))) -> list[OrderLine]:
    # Convenience endpoint for the client when it wants to focus only on the order rows.
    return get_order_or_404(order_id).lines


@app.post("/orders", response_model=OrderDetail, status_code=status.HTTP_201_CREATED, responses=PROTECTED)
def create_order(order: OrderCreate, _payload: dict = Depends(require_role("orders:write"))) -> OrderDetail:
    # Create a new order in memory and return the stored representation with generated ids.
    return create_order_record(order)
