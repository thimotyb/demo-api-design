import pytest
from fastapi.testclient import TestClient

from graphql_api.app import create_app, schema
from shared.domain import Store

AUTHORIZE = """
mutation Authorize($input: AuthorizePaymentInput!) {
  authorizePayment(input: $input) { id status replayed amount { amount currency } }
}
"""


def payment_input(token="tok_demo_visa", amount="19.90", key=None):
    data = {"customerId": "c-001", "amount": {"amount": amount, "currency": "EUR"}, "paymentToken": token}
    if key:
        data["idempotencyKey"] = key
    return {"input": data}


@pytest.fixture
def store():
    return Store()


@pytest.fixture
def client(store):
    return TestClient(create_app(store))


def gql(client, query, variables=None):
    response = client.post("/graphql", json={"query": query, "variables": variables or {}})
    assert response.status_code == 200  # GraphQL reports failures in the body
    return response.json()


def test_one_query_returns_the_order_and_its_shipment(client):
    body = gql(client, "{ order(id: \"o-1001\") { id status shipment { status lastEvent { location } } } }")
    assert "errors" not in body
    order = body["data"]["order"]
    assert order["status"] == "SHIPPED"
    assert order["shipment"] == {"status": "IN_TRANSIT", "lastEvent": {"location": "Bologna hub"}}


def test_the_response_contains_only_the_requested_fields(client):
    body = gql(client, "{ order(id: \"o-1001\") { id } }")
    assert body["data"] == {"order": {"id": "o-1001"}}


def test_unknown_order_is_http_200_with_a_coded_error(client):
    body = gql(client, "{ order(id: \"nope\") { id } }")
    assert body["data"] is None
    assert body["errors"][0]["extensions"]["code"] == "ORDER_NOT_FOUND"


def test_invalid_query_is_rejected_before_execution(client):
    body = gql(client, "{ order(id: \"o-1001\") { doesNotExist } }")
    assert "doesNotExist" in body["errors"][0]["message"]


def test_payment_replay_with_the_same_key(client, store):
    first = gql(client, AUTHORIZE, payment_input(key="k-1"))["data"]["authorizePayment"]
    second = gql(client, AUTHORIZE, payment_input(key="k-1"))["data"]["authorizePayment"]
    assert first["replayed"] is False and second["replayed"] is True
    assert first["id"] == second["id"]
    assert store.gateway.calls == 1


def test_same_key_with_a_different_request_is_a_coded_error(client):
    gql(client, AUTHORIZE, payment_input(key="k-2"))
    body = gql(client, AUTHORIZE, payment_input(key="k-2", amount="25.00"))
    assert body["errors"][0]["extensions"]["code"] == "IDEMPOTENCY_CONFLICT"


def test_transient_failure_then_retry_with_the_same_key(client, store):
    first = gql(client, AUTHORIZE, payment_input(token="tok_flaky", key="k-3"))
    second = gql(client, AUTHORIZE, payment_input(token="tok_flaky", key="k-3"))
    assert first["errors"][0]["extensions"]["code"] == "TRANSIENT_GATEWAY_FAILURE"
    assert second["data"]["authorizePayment"]["status"] == "AUTHORIZED"
    assert store.gateway.calls == 2


def test_evolution_new_field_added_old_fields_deprecated(client):
    sdl = schema.as_str()
    assert "total: Money!" in sdl
    assert 'totalAmount: Decimal! @deprecated(reason: "Use total.amount")' in sdl
    # An old client that still asks for the deprecated fields keeps working.
    body = gql(client, "{ order(id: \"o-1001\") { totalAmount currency } }")
    assert body["data"]["order"] == {"totalAmount": "64.50", "currency": "EUR"}
