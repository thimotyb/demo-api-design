import pytest
from fastapi.testclient import TestClient

from graphql_api.app import create_app, rest_client, schema
from rest_api.app import create_app as create_rest
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
    return TestClient(create_app(rest_client(create_rest(store))))


def gql(client, query, variables=None):
    response = client.post("/graphql", json={"query": query, "variables": variables or {}})
    assert response.status_code == 200  # GraphQL reports failures in the body
    return response.json()


# GraphQL fetches the order and its nested shipment in a single request, where REST needs two.
def test_one_query_returns_the_order_and_its_shipment(client):
    body = gql(client, "{ order(id: \"o-1001\") { id status shipment { status lastEvent { location } } } }")
    assert "errors" not in body
    order = body["data"]["order"]
    assert order["status"] == "SHIPPED"
    assert order["shipment"] == {"status": "IN_TRANSIT", "lastEvent": {"location": "Bologna hub"}}


# The response has exactly the fields named in the query and nothing else (no over-fetching).
def test_the_response_contains_only_the_requested_fields(client):
    body = gql(client, "{ order(id: \"o-1001\") { id } }")
    assert body["data"] == {"order": {"id": "o-1001"}}


# GraphQL reports failures in the body: HTTP 200, `data` is null and `errors` carries the domain code.
def test_unknown_order_is_http_200_with_a_coded_error(client):
    body = gql(client, "{ order(id: \"nope\") { id } }")
    assert body["data"] is None
    assert body["errors"][0]["extensions"]["code"] == "ORDER_NOT_FOUND"


# A query asking for a field that is not in the schema is rejected by validation and never executed.
def test_invalid_query_is_rejected_before_execution(client):
    body = gql(client, "{ order(id: \"o-1001\") { doesNotExist } }")
    assert "doesNotExist" in body["errors"][0]["message"]


# Idempotency in GraphQL: the same key twice returns the same payment, flagged `replayed`, with one gateway call.
def test_payment_replay_with_the_same_key(client, store):
    first = gql(client, AUTHORIZE, payment_input(key="k-1"))["data"]["authorizePayment"]
    second = gql(client, AUTHORIZE, payment_input(key="k-1"))["data"]["authorizePayment"]
    assert first["replayed"] is False and second["replayed"] is True
    assert first["id"] == second["id"]
    assert store.gateway.calls == 1


# Reusing a key with a different input returns an IDEMPOTENCY_CONFLICT error in the body.
def test_same_key_with_a_different_request_is_a_coded_error(client):
    gql(client, AUTHORIZE, payment_input(key="k-2"))
    body = gql(client, AUTHORIZE, payment_input(key="k-2", amount="25.00"))
    assert body["errors"][0]["extensions"]["code"] == "IDEMPOTENCY_CONFLICT"


# A temporary gateway failure is reported as an error, and the retry with the same key succeeds (AUTHORIZED).
def test_transient_failure_then_retry_with_the_same_key(client, store):
    first = gql(client, AUTHORIZE, payment_input(token="tok_flaky", key="k-3"))
    second = gql(client, AUTHORIZE, payment_input(token="tok_flaky", key="k-3"))
    assert first["errors"][0]["extensions"]["code"] == "TRANSIENT_GATEWAY_FAILURE"
    assert second["data"]["authorizePayment"]["status"] == "AUTHORIZED"
    assert store.gateway.calls == 2


# Schema evolution: the new `total` field is added and the old ones are marked @deprecated, but old queries still work.
def test_evolution_new_field_added_old_fields_deprecated(client):
    sdl = schema.as_str()
    assert "total: Money!" in sdl
    assert 'totalAmount: Decimal! @deprecated(reason: "Use total.amount")' in sdl
    # An old client that still asks for the deprecated fields keeps working.
    body = gql(client, "{ order(id: \"o-1001\") { totalAmount currency } }")
    assert body["data"]["order"] == {"totalAmount": "64.50", "currency": "EUR"}


# The GraphQL server holds no data: every field it returns is read from the REST API, and only the fields the
# query selects trigger a REST call.
def test_resolvers_call_the_rest_api_only_for_the_selected_fields(store):
    calls = []

    async def record(request):
        calls.append(f"{request.method} {request.url.path}")

    rest = rest_client(create_rest(store))
    rest.event_hooks["request"].append(record)
    client = TestClient(create_app(rest))

    gql(client, '{ order(id: "o-1001") { id status } }')
    assert calls == ["GET /v2/orders/o-1001"]

    calls.clear()
    gql(client, '{ order(id: "o-1001") { shipment { status } customer { email } } }')
    assert calls == ["GET /v2/orders/o-1001", "GET /v1/orders/o-1001/shipment", "GET /v1/customers/c-001"]


# The idempotency key of the GraphQL input travels to the REST API as the Idempotency-Key header.
def test_the_idempotency_key_is_forwarded_as_a_header(store):
    seen = []

    async def record(request):
        seen.append(request.headers.get("idempotency-key"))

    rest = rest_client(create_rest(store))
    rest.event_hooks["request"].append(record)
    gql(TestClient(create_app(rest)), AUTHORIZE, payment_input(key="k-9"))
    assert seen == ["k-9"]


# A REST error body becomes a GraphQL error with the same code.
def test_an_unknown_customer_is_a_coded_error_from_the_rest_api(client, store):
    store.orders["o-1001"].customer_id = "c-404"
    body = gql(client, '{ order(id: "o-1001") { customer { email } } }')
    assert body["errors"][0]["extensions"]["code"] == "CUSTOMER_NOT_FOUND"
