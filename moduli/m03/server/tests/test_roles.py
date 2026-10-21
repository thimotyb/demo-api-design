"""Role checks of the Orders API, with the token validation replaced by a stub.

The tests do not need Keycloak: they replace decode_access_token, so they check what the API
does with the claims, not how the signature is verified.
Run from moduli/m03/server:  python -m pytest
"""
import pytest
from fastapi.testclient import TestClient

from app import main
from app.auth import token_roles

client = TestClient(main.app)

NEW_ORDER = {"customer": "Test Srl", "lines": [{"sku": "A", "description": "Item", "quantity": 1, "unit_price": 2.5}]}


def with_roles(monkeypatch, *roles: str):
    """Make every bearer token decode to claims that carry the given realm roles."""
    claims = {"azp": "m3-fastapi-client", "realm_access": {"roles": list(roles)}}
    monkeypatch.setattr(main, "decode_access_token", lambda token: claims)
    return {"Authorization": "Bearer any-token"}


def test_token_roles_reads_the_realm_access_claim():
    assert token_roles({"realm_access": {"roles": ["orders:read"]}}) == {"orders:read"}
    assert token_roles({}) == set()


def test_reader_can_list_and_read(monkeypatch):
    headers = with_roles(monkeypatch, "orders:read")
    assert client.get("/orders", headers=headers).status_code == 200
    assert client.get("/orders/1001", headers=headers).status_code == 200
    assert client.get("/orders/1001/lines", headers=headers).status_code == 200


def test_reader_cannot_create_an_order(monkeypatch):
    """A valid token with only orders:read is authenticated but not allowed: 403, not 401."""
    headers = with_roles(monkeypatch, "orders:read")
    response = client.post("/orders", json=NEW_ORDER, headers=headers)
    assert response.status_code == 403
    assert "orders:write" in response.json()["detail"]


def test_writer_can_create_an_order(monkeypatch):
    headers = with_roles(monkeypatch, "orders:read", "orders:write")
    response = client.post("/orders", json=NEW_ORDER, headers=headers)
    assert response.status_code == 201


@pytest.mark.parametrize("path", ["/orders", "/orders/1001", "/orders/1001/lines"])
def test_write_role_alone_does_not_allow_reading(monkeypatch, path):
    """Roles are separate permissions: orders:write does not imply orders:read."""
    headers = with_roles(monkeypatch, "orders:write")
    assert client.get(path, headers=headers).status_code == 403


def test_token_without_any_role_is_refused(monkeypatch):
    monkeypatch.setattr(main, "decode_access_token", lambda token: {"azp": "m3-fastapi-client"})
    headers = {"Authorization": "Bearer any-token"}
    assert client.get("/orders", headers=headers).status_code == 403


def test_missing_token_is_401_not_403():
    """No credential at all is an authentication failure, answered before any role check."""
    response = client.get("/orders")
    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"


def test_root_stays_public():
    assert client.get("/").status_code == 200


# OpenAPI: the contract declares how the API is protected ------------------------------

def test_openapi_declares_the_client_credentials_scheme():
    """The scheme in the OpenAPI document is what shows the Authorize button in /docs."""
    scheme = client.get("/openapi.json").json()["components"]["securitySchemes"]["OAuth2ClientCredentials"]
    assert scheme["type"] == "oauth2"
    assert scheme["flows"]["clientCredentials"]["tokenUrl"].endswith("/protocol/openid-connect/token")


def test_openapi_marks_the_orders_operations_as_protected_and_root_as_public():
    paths = client.get("/openapi.json").json()["paths"]
    for path, method in [("/orders", "get"), ("/orders", "post"), ("/orders/{order_id}", "get"), ("/orders/{order_id}/lines", "get")]:
        operation = paths[path][method]
        assert operation["security"] == [{"OAuth2ClientCredentials": []}]
        assert {"401", "403"} <= set(operation["responses"])
    assert "security" not in paths["/"]["get"]
